"use client";

import { useState } from "react";
import { CheckCircle, ExternalLink, Loader2, Send } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { updatePortal, testPortalNotification } from "@/lib/api";
import { toast } from "sonner";

interface NotificationSettingsProps {
  slug: string;
  slackWebhookUrl: string | null;
  onSaved: (url: string | null) => void;
  compact?: boolean;
}

function SlackIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.527 2.527 0 0 1 2.521 2.521 2.527 2.527 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zm10.124 2.521a2.528 2.528 0 0 1 2.52-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.52V8.834zm-1.271 0a2.527 2.527 0 0 1-2.521 2.521 2.527 2.527 0 0 1-2.521-2.521V2.522A2.528 2.528 0 0 1 15.166 0a2.528 2.528 0 0 1 2.521 2.522v6.312zm-2.521 10.124a2.528 2.528 0 0 1 2.521 2.52A2.528 2.528 0 0 1 15.166 24a2.528 2.528 0 0 1-2.521-2.522v-2.52h2.521zm0-1.271a2.527 2.527 0 0 1-2.521-2.521 2.527 2.527 0 0 1 2.521-2.521h6.312A2.528 2.528 0 0 1 24 15.166a2.528 2.528 0 0 1-2.522 2.521h-6.312z" />
    </svg>
  );
}

export function NotificationSettings({ slug, slackWebhookUrl, onSaved, compact }: NotificationSettingsProps) {
  const [url, setUrl] = useState(slackWebhookUrl ?? "");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const isConnected = !!slackWebhookUrl;
  const isDirty = url !== (slackWebhookUrl ?? "");

  async function handleSave() {
    setSaving(true);
    try {
      const value = url.trim() || undefined;
      await updatePortal(slug, { slack_webhook_url: value || "" });
      onSaved(value || null);
      toast.success(value ? "Slack webhook saved" : "Slack webhook removed");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    try {
      await testPortalNotification(slug);
      toast.success("Test notification sent — check Slack");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Test failed");
    } finally {
      setTesting(false);
    }
  }

  if (compact) {
    return (
      <div className="rounded-lg border border-clay-700 bg-clay-800 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlackIcon className="h-4 w-4 text-clay-400" />
            <span className="text-xs font-medium text-clay-200">Slack</span>
            {isConnected ? (
              <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Connected
              </span>
            ) : (
              <span className="text-[10px] text-clay-500">Not connected</span>
            )}
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[11px] text-clay-400 hover:text-clay-200"
          >
            {expanded ? "Close" : "Edit"}
          </button>
        </div>
        {expanded && (
          <div className="mt-3 space-y-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              className="w-full rounded-md border border-clay-600 bg-clay-900 px-2.5 py-1.5 text-xs text-clay-100 placeholder:text-clay-500 focus:border-clay-400 focus:outline-none"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={handleSave}
                disabled={saving || !isDirty}
                className="inline-flex items-center gap-1 rounded-md bg-clay-600 px-2.5 py-1 text-[11px] font-medium text-clay-100 hover:bg-clay-500 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-3 w-3" />}
                Save
              </button>
              {isConnected && (
                <button
                  onClick={handleTest}
                  disabled={testing || isDirty}
                  className="inline-flex items-center gap-1 rounded-md border border-clay-600 px-2.5 py-1 text-[11px] font-medium text-clay-300 hover:bg-clay-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {testing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
                  Test
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className="relative inline-flex items-center justify-center h-8 w-8 rounded-md border border-clay-600 bg-clay-800 text-clay-400 hover:text-clay-100 hover:bg-clay-700 transition-colors"
          title={isConnected ? "Slack connected" : "Set up Slack notifications"}
        >
          <SlackIcon className="h-4 w-4" />
          {isConnected && (
            <span className="absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full bg-emerald-400 border-2 border-clay-800" />
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 border-clay-600 bg-clay-800 p-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-clay-100">Slack Notifications</h4>
            {isConnected && (
              <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Connected
              </span>
            )}
          </div>
          <p className="text-xs text-clay-400">
            Paste an{" "}
            <a
              href="https://api.slack.com/messaging/webhooks"
              target="_blank"
              rel="noopener noreferrer"
              className="text-clay-300 underline underline-offset-2 hover:text-clay-100 inline-flex items-center gap-0.5"
            >
              Incoming Webhook
              <ExternalLink className="h-2.5 w-2.5" />
            </a>{" "}
            URL.
          </p>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://hooks.slack.com/services/..."
            className="w-full rounded-md border border-clay-600 bg-clay-900 px-2.5 py-1.5 text-xs text-clay-100 placeholder:text-clay-500 focus:border-clay-400 focus:outline-none"
          />
          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={saving || !isDirty}
              className="inline-flex items-center gap-1 rounded-md bg-clay-600 px-2.5 py-1 text-[11px] font-medium text-clay-100 hover:bg-clay-500 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-3 w-3" />}
              Save
            </button>
            {isConnected && (
              <button
                onClick={handleTest}
                disabled={testing || isDirty}
                className="inline-flex items-center gap-1 rounded-md border border-clay-600 px-2.5 py-1 text-[11px] font-medium text-clay-300 hover:bg-clay-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {testing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
                Test
              </button>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
