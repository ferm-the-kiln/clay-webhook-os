"use client";

import { useState } from "react";
import type { WebhookResponse } from "@/lib/types";
import { formatSmartDuration } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Clock, Trash2 } from "lucide-react";

export interface HistoryEntry {
  id: string;
  skill: string;
  model: string;
  input: string;
  result: WebhookResponse;
  timestamp: number;
}

const STORAGE_KEY = "clay-playground-history";
const MAX_ENTRIES = 10;

export function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveToHistory(entry: Omit<HistoryEntry, "id" | "timestamp">) {
  const history = loadHistory();
  const newEntry: HistoryEntry = {
    ...entry,
    id: crypto.randomUUID(),
    timestamp: Date.now(),
  };
  const updated = [newEntry, ...history].slice(0, MAX_ENTRIES);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return updated;
}

export function clearHistory() {
  localStorage.removeItem(STORAGE_KEY);
}

export function RunHistory({
  history,
  onRestore,
  onClear,
}: {
  history: HistoryEntry[];
  onRestore: (entry: HistoryEntry) => void;
  onClear: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          className="relative p-1.5 rounded transition-colors text-clay-500 hover:text-clay-300"
          title="Run history"
        >
          <Clock className="h-4 w-4" />
          {history.length > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center h-3.5 min-w-3.5 rounded-full bg-kiln-teal text-clay-950 text-[9px] font-bold px-0.5">
              {history.length}
            </span>
          )}
        </button>
      </SheetTrigger>
      <SheetContent className="w-full sm:max-w-md bg-clay-950 border-clay-800 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-clay-100">Run History</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-2">
          {history.length === 0 && (
            <p className="text-sm text-clay-500 text-center py-8">
              No runs yet. Results will appear here after you run a skill.
            </p>
          )}
          {history.map((entry) => {
            const meta = entry.result._meta;
            const isError = entry.result.error;
            return (
              <button
                key={entry.id}
                onClick={() => {
                  onRestore(entry);
                  setOpen(false);
                }}
                className="w-full text-left rounded-lg border border-clay-800 bg-clay-900 p-3 hover:border-kiln-teal/30 transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-clay-200">
                    {entry.skill}
                  </span>
                  <span className="text-xs text-clay-500">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={`text-[10px] ${
                      isError
                        ? "border-kiln-coral/30 text-kiln-coral"
                        : "border-kiln-teal/30 text-kiln-teal"
                    }`}
                  >
                    {isError ? "error" : "success"}
                  </Badge>
                  <Badge variant="outline" className="text-[10px] border-clay-700 text-clay-400">
                    {entry.model}
                  </Badge>
                  {meta?.duration_ms && (
                    <span className="text-[10px] text-clay-500">
                      {formatSmartDuration(meta.duration_ms)}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
          {history.length > 0 && (
            <button
              onClick={() => {
                onClear();
                setOpen(false);
              }}
              className="flex items-center gap-1.5 text-xs text-clay-500 hover:text-kiln-coral transition-colors mx-auto pt-2"
            >
              <Trash2 className="h-3 w-3" />
              Clear history
            </button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
