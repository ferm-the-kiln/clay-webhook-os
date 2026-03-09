"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Send, Check, Loader2, ChevronDown, AlertCircle } from "lucide-react";
import { fetchDestinations, pushDataToDestination } from "@/lib/api";
import type { Destination } from "@/lib/types";

export function PushToDestination({
  data,
  className,
}: {
  data: Record<string, unknown> | null;
  className?: string;
}) {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [open, setOpen] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [pushResult, setPushResult] = useState<{
    ok: boolean;
    name: string;
    error?: string;
  } | null>(null);

  useEffect(() => {
    if (!loaded) {
      fetchDestinations()
        .then((r) => {
          setDestinations(r.destinations);
          setLoaded(true);
        })
        .catch(() => setLoaded(true));
    }
  }, [loaded]);

  const handlePush = async (dest: Destination) => {
    if (!data) return;
    setPushing(true);
    setPushResult(null);
    try {
      const res = await pushDataToDestination(dest.id, data);
      setPushResult({
        ok: res.ok,
        name: res.destination_name,
        error: res.error,
      });
    } catch (e) {
      setPushResult({
        ok: false,
        name: dest.name,
        error: e instanceof Error ? e.message : "Push failed",
      });
    } finally {
      setPushing(false);
      setTimeout(() => setPushResult(null), 4000);
    }
  };

  if (!data) return null;

  // No destinations configured
  if (loaded && destinations.length === 0) {
    return (
      <Button
        variant="ghost"
        size="sm"
        disabled
        className={cn(
          "text-xs text-clay-400 h-7 cursor-not-allowed",
          className
        )}
        title="No destinations configured. Set up destinations in Settings."
      >
        <Send className="h-3.5 w-3.5 mr-1" />
        Push to Clay
      </Button>
    );
  }

  return (
    <div className={cn("relative", className)}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen(!open)}
        disabled={pushing}
        className="text-xs text-clay-300 hover:text-kiln-teal h-7"
      >
        {pushing ? (
          <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
        ) : pushResult?.ok ? (
          <Check className="h-3.5 w-3.5 mr-1 text-emerald-400" />
        ) : pushResult && !pushResult.ok ? (
          <AlertCircle className="h-3.5 w-3.5 mr-1 text-red-400" />
        ) : (
          <Send className="h-3.5 w-3.5 mr-1" />
        )}
        {pushResult
          ? pushResult.ok
            ? `Pushed to ${pushResult.name}`
            : pushResult.error ?? "Push failed"
          : "Push to Clay"}
        <ChevronDown className="h-3 w-3 ml-1" />
      </Button>

      {/* Dropdown */}
      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute bottom-full mb-1 right-0 z-50 w-48 rounded-lg border border-clay-700 bg-clay-800 shadow-xl py-1">
            {destinations.map((dest) => (
              <button
                key={dest.id}
                onClick={() => {
                  handlePush(dest);
                  setOpen(false);
                }}
                className="w-full text-left px-3 py-2 text-xs text-clay-200 hover:bg-clay-700/50 transition-colors"
              >
                <span className="font-medium block">{dest.name}</span>
                <span className="text-[10px] text-clay-400">{dest.type}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
