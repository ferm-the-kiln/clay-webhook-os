"use client";

import { useState, useEffect, useCallback } from "react";
import { CheckCircle2, Circle, Loader2, Terminal, Copy, ExternalLink, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getLocalRunnerStatus } from "@/lib/api";

const SETUP_COMMAND = `cd ~/Documents/clay-webhook-os && python3.11 scripts/clay-run.py --watch`;

export default function SetupPage() {
  const [copied, setCopied] = useState(false);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);

  const checkStatus = useCallback(async () => {
    setChecking(true);
    try {
      const status = await getLocalRunnerStatus();
      setConnected(status.connected);
    } catch {
      setConnected(false);
    } finally {
      setChecking(false);
    }
  }, []);

  // Poll for connection on mount
  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, [checkStatus]);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(SETUP_COMMAND);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const steps = [
    {
      title: "Install Claude Code",
      description: "This is the AI engine that powers your enrichments. Download it and sign in with your Claude account.",
      action: (
        <Button variant="outline" size="sm" className="h-7 border-clay-600 text-clay-300" asChild>
          <a href="https://claude.ai/download" target="_blank" rel="noopener noreferrer">
            <ExternalLink className="h-3 w-3 mr-1" />Download
          </a>
        </Button>
      ),
      hint: "Already have it? Skip to step 2.",
    },
    {
      title: "Start the runner in Terminal",
      description: "Open the Terminal app on your Mac (search \"Terminal\" in Spotlight) and paste the command below. Keep this terminal open while you work.",
      action: (
        <div className="space-y-2 w-full">
          <div
            onClick={handleCopy}
            className="flex items-center gap-2 bg-clay-900 border border-clay-700 rounded-lg px-4 py-3 cursor-pointer hover:border-clay-600 transition-colors group"
          >
            <code className="text-xs text-kiln-teal font-mono flex-1 break-all select-all">
              {SETUP_COMMAND}
            </code>
            <button className="shrink-0 text-clay-500 group-hover:text-clay-300 transition-colors">
              {copied ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
            </button>
          </div>
          <p className="text-[10px] text-clay-500">
            Click to copy. After pasting, the runner will start polling for jobs.
          </p>
        </div>
      ),
    },
    {
      title: "You're all set",
      description: connected
        ? "Connected and ready to go. Enrichments will run on your computer."
        : "Waiting for the runner to connect — this usually takes a few seconds after step 2.",
      action: connected ? (
        <Button size="sm" className="h-8 bg-kiln-teal text-black hover:bg-kiln-teal/90" asChild>
          <a href="/enrich">
            <Zap className="h-3.5 w-3.5 mr-1" />Start Enriching
          </a>
        </Button>
      ) : (
        <Button variant="outline" size="sm" className="h-7 border-clay-600 text-clay-300" onClick={checkStatus} disabled={checking}>
          {checking ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Circle className="h-3 w-3 mr-1" />}
          Check again
        </Button>
      ),
    },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto py-12 px-6">
        <div className="max-w-lg mx-auto space-y-8">
          {/* Header */}
          <div className="text-center space-y-2">
            <div className="flex items-center justify-center gap-2 mb-4">
              <Terminal className="h-6 w-6 text-kiln-teal" />
            </div>
            <h1 className="text-xl font-semibold text-clay-100">Start the local runner</h1>
            <p className="text-sm text-clay-400 max-w-sm mx-auto">
              Enrichments run directly on your Mac. Start the runner in Terminal and keep it open while you work.
            </p>
          </div>

          {/* Steps */}
          <div className="space-y-1">
            {steps.map((step, i) => {
              const isDone = i === 2 ? connected === true : i < 2;
              // Step 3 is "done" when connected
              // Steps 1-2 we can't detect, so always show as available

              return (
                <div key={i} className="flex gap-4">
                  {/* Vertical line + dot */}
                  <div className="flex flex-col items-center">
                    <div className={cn(
                      "h-8 w-8 rounded-full flex items-center justify-center shrink-0 border-2 transition-colors",
                      i === 2 && connected === true
                        ? "border-emerald-500 bg-emerald-500/10"
                        : "border-clay-600 bg-clay-800",
                    )}>
                      {i === 2 && connected === true ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <span className="text-xs font-semibold text-clay-300">{i + 1}</span>
                      )}
                    </div>
                    {i < steps.length - 1 && <div className="w-px flex-1 bg-clay-700 my-1" />}
                  </div>

                  {/* Content */}
                  <div className="pb-8 flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-clay-100 mb-1">{step.title}</h3>
                    <p className="text-xs text-clay-400 mb-3 leading-relaxed">{step.description}</p>
                    {step.action}
                    {step.hint && <p className="text-[10px] text-clay-500 mt-2">{step.hint}</p>}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Status card */}
          <div className={cn(
            "rounded-lg border px-4 py-3 flex items-center gap-3",
            connected === true
              ? "border-emerald-500/20 bg-emerald-500/5"
              : "border-clay-700 bg-clay-800/50",
          )}>
            <div className={cn(
              "h-2.5 w-2.5 rounded-full shrink-0",
              connected === true ? "bg-emerald-500" : connected === false ? "bg-red-500 animate-pulse" : "bg-clay-500",
            )} />
            <div className="flex-1">
              <span className={cn("text-sm", connected === true ? "text-emerald-300" : "text-clay-300")}>
                {connected === true
                  ? "Connected"
                  : connected === false
                    ? "Not connected"
                    : "Checking..."}
              </span>
            </div>
            {connected === true && (
              <span className="text-[10px] text-clay-500">Runner active</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
