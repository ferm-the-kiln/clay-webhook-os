#!/usr/bin/env bun
/**
 * Clay Chat Channel — Two-way MCP channel server using the official
 * Claude Code Channels API.
 *
 * Claude Code spawns this as a subprocess and communicates over stdio.
 * The HTTP server on :8789 bridges the dashboard to the Claude session:
 *
 *   POST /message        — Push a user message into the Claude session
 *   GET  /events/:chatId — SSE stream of Claude replies for a given chat
 *   GET  /health         — Liveness probe
 *
 * Claude reads events as <channel source="clay-chat" chat_id="...">
 * and calls the `reply` tool to send responses back.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const PORT = parseInt(process.env.CHANNEL_PORT || "8789", 10);

// ── Outbound: SSE listeners keyed by chat_id ─────────────────────

type SSEWriter = (event: string, data: string) => void;
const listeners = new Map<string, Set<SSEWriter>>();

function addListener(chatId: string, writer: SSEWriter): () => void {
  if (!listeners.has(chatId)) listeners.set(chatId, new Set());
  listeners.get(chatId)!.add(writer);
  return () => {
    listeners.get(chatId)?.delete(writer);
    if (listeners.get(chatId)?.size === 0) listeners.delete(chatId);
  };
}

function broadcast(chatId: string, event: string, data: string) {
  const set = listeners.get(chatId);
  if (!set) return;
  for (const writer of set) {
    try {
      writer(event, data);
    } catch {
      // Client disconnected
    }
  }
}

// ── MCP Channel Server ───────────────────────────────────────────

const mcp = new Server(
  { name: "clay-chat", version: "1.0.0" },
  {
    capabilities: {
      // This is what makes it a channel — Claude Code registers a listener
      experimental: { "claude/channel": {} },
      // Enable tool discovery for the reply tool
      tools: {},
    },
    // Added to Claude's system prompt so it knows how to handle events
    instructions:
      "You are the Clay Webhook OS assistant. You have READ-ONLY access to all project files " +
      "including skills, knowledge base, client profiles, functions, and configuration. " +
      "Answer questions accurately by reading the relevant files. " +
      "Be concise and helpful. Use markdown formatting for readability.\n\n" +
      'Messages arrive as <channel source="clay-chat" chat_id="...">. ' +
      "Reply using the reply tool, always passing the chat_id from the incoming tag. " +
      "Each chat_id represents a different user conversation — keep them separate.",
  }
);

// ── Reply tool: Claude calls this to send responses back ─────────

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "reply",
      description: "Send a reply back to the user in their chat session",
      inputSchema: {
        type: "object" as const,
        properties: {
          chat_id: {
            type: "string",
            description: "The chat_id from the incoming channel message",
          },
          text: {
            type: "string",
            description: "Your response text (supports markdown)",
          },
        },
        required: ["chat_id", "text"],
      },
    },
  ],
}));

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  if (req.params.name === "reply") {
    const { chat_id, text } = req.params.arguments as {
      chat_id: string;
      text: string;
    };

    // Broadcast to SSE listeners for this chat
    broadcast(chat_id, "chunk", JSON.stringify({ chat_id, text }));
    broadcast(chat_id, "done", JSON.stringify({ chat_id }));

    return { content: [{ type: "text" as const, text: `Reply sent to ${chat_id}` }] };
  }
  throw new Error(`Unknown tool: ${req.params.name}`);
});

// ── Connect to Claude Code over stdio ────────────────────────────

await mcp.connect(new StdioServerTransport());

// ── HTTP Server (dashboard bridge) ───────────────────────────────

Bun.serve({
  port: PORT,
  hostname: "127.0.0.1",
  idleTimeout: 0, // Don't close idle SSE streams

  async fetch(req) {
    const url = new URL(req.url);

    // CORS headers for dashboard
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    // POST /message — Push user message into Claude session
    if (req.method === "POST" && url.pathname === "/message") {
      try {
        const body = (await req.json()) as {
          chat_id: string;
          content: string;
        };
        if (!body.chat_id || !body.content) {
          return Response.json(
            { error: "chat_id and content required" },
            { status: 400, headers: corsHeaders }
          );
        }

        // Push into Claude session as a channel notification
        await mcp.notification({
          method: "notifications/claude/channel",
          params: {
            content: body.content,
            meta: { chat_id: body.chat_id },
          },
        });

        return Response.json(
          { ok: true, chat_id: body.chat_id },
          { headers: corsHeaders }
        );
      } catch (e) {
        return Response.json(
          { error: "Failed to push message", detail: String(e) },
          { status: 500, headers: corsHeaders }
        );
      }
    }

    // GET /events/:chatId — SSE stream of replies
    if (req.method === "GET" && url.pathname.startsWith("/events/")) {
      const chatId = url.pathname.slice("/events/".length);
      if (!chatId) {
        return Response.json(
          { error: "chat_id required in path" },
          { status: 400, headers: corsHeaders }
        );
      }

      const stream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          const writer: SSEWriter = (event, data) => {
            controller.enqueue(
              encoder.encode(`event: ${event}\ndata: ${data}\n\n`)
            );
          };

          // Send initial connected event
          writer("connected", JSON.stringify({ chat_id: chatId }));

          const cleanup = addListener(chatId, writer);

          req.signal.addEventListener("abort", () => {
            cleanup();
            try {
              controller.close();
            } catch {
              // Already closed
            }
          });
        },
      });

      return new Response(stream, {
        headers: {
          ...corsHeaders,
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
          "X-Accel-Buffering": "no",
        },
      });
    }

    // GET /health
    if (req.method === "GET" && url.pathname === "/health") {
      return Response.json(
        {
          status: "ok",
          active_listeners: listeners.size,
        },
        { headers: corsHeaders }
      );
    }

    return Response.json(
      { error: "Not found" },
      { status: 404, headers: corsHeaders }
    );
  },
});

console.error(
  `Clay Chat Channel server listening on http://localhost:${PORT}`
);
