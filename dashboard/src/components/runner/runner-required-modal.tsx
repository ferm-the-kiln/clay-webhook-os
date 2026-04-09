"use client";

import { useState, useEffect, useCallback } from "react";
import { CheckCircle2, Copy, ExternalLink, Terminal } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getLocalRunnerStatus } from "@/lib/api";

const WATCH_COMMAND = `cd ~/Documents/clay-webhook-os && python3.11 scripts/clay-run.py --watch`;

interface RunnerRequiredModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnected: () => void;
}

export function RunnerRequiredModal({ open, onOpenChange, onConnected }: RunnerRequiredModalProps) {
  const [copied, setCopied] = useState(false);
  const [connected, setConnected] = useState(false);

  // Poll for connection while modal is open
  useEffect(() => {
    if (!open) {
      setConnected(false);
      return;
    }
    let active = true;
    const check = () => {
      getLocalRunnerStatus()
        .then((s) => {
          if (!active) return;
          if (s.connected) {
            setConnected(true);
            // Brief delay for visual feedback, then fire callback
            setTimeout(() => {
              if (active) onConnected();
            }, 600);
          }
        })
        .catch(() => {});
    };
    check();
    const interval = setInterval(check, 3000);
    return () => { active = false; clearInterval(interval); };
  }, [open, onConnected]);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(WATCH_COMMAND);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-kiln-teal" />
            Start local runner
          </DialogTitle>
        </DialogHeader>

        <div className="px-5 py-4 space-y-5">
          {/* Step 1 */}
          <div className="flex gap-3">
            <div className="h-6 w-6 rounded-full border border-clay-600 bg-clay-800 flex items-center justify-center shrink-0 mt-0.5">
              <span className="text-[10px] font-semibold text-clay-300">1</span>
            </div>
            <div className="space-y-1.5">
              <p className="text-sm text-clay-200 font-medium">Install Claude Code</p>
              <p className="text-xs text-clay-400">The AI engine that powers enrichments.</p>
              <Button variant="outline" size="sm" className="h-7 border-clay-600 text-clay-300" asChild>
                <a href="https://claude.ai/download" target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-3 w-3 mr-1" />Download
                </a>
              </Button>
              <p className="text-[10px] text-clay-500">Already installed? Skip to step 2.</p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="flex gap-3">
            <div className="h-6 w-6 rounded-full border border-clay-600 bg-clay-800 flex items-center justify-center shrink-0 mt-0.5">
              <span className="text-[10px] font-semibold text-clay-300">2</span>
            </div>
            <div className="space-y-1.5 flex-1 min-w-0">
              <p className="text-sm text-clay-200 font-medium">Start the local runner</p>
              <p className="text-xs text-clay-400">Open Terminal and paste this command. Keep it running while you work.</p>
              <div
                onClick={handleCopy}
                className="flex items-center gap-2 bg-clay-900 border border-clay-700 rounded-lg px-3 py-2.5 cursor-pointer hover:border-clay-600 transition-colors group"
              >
                <code className="text-[11px] text-kiln-teal font-mono flex-1 break-all select-all">
                  {WATCH_COMMAND}
                </code>
                <button className="shrink-0 text-clay-500 group-hover:text-clay-300 transition-colors">
                  {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>
          </div>

          {/* Connection status */}
          <div className={cn(
            "rounded-lg border px-3 py-2.5 flex items-center gap-2.5",
            connected
              ? "border-emerald-500/20 bg-emerald-500/5"
              : "border-clay-700 bg-clay-800/50",
          )}>
            <div className={cn(
              "h-2 w-2 rounded-full shrink-0 transition-colors",
              connected ? "bg-emerald-500" : "bg-red-500 animate-pulse",
            )} />
            <span className={cn("text-xs", connected ? "text-emerald-300" : "text-clay-400")}>
              {connected ? "Connected — starting your run..." : "Waiting for local runner..."}
            </span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
