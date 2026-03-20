"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { EmailLabRun } from "@/lib/email-lab-constants";
import { cn } from "@/lib/utils";

function extractBody(run: EmailLabRun): string {
  const r = run.result;
  return (
    (r?.body as string) ||
    (r?.email_body as string) ||
    (r?.email as string) ||
    ""
  );
}

function extractSubject(run: EmailLabRun): string {
  const r = run.result;
  return (
    (r?.subject as string) ||
    (r?.subject_line as string) ||
    (r?.email_subject as string) ||
    ""
  );
}

function wordDiff(a: string, b: string): { aTokens: DiffToken[]; bTokens: DiffToken[] } {
  const aWords = a.split(/(\s+)/);
  const bWords = b.split(/(\s+)/);
  const aSet = new Set(aWords.filter((w) => w.trim()));
  const bSet = new Set(bWords.filter((w) => w.trim()));

  const aTokens: DiffToken[] = aWords.map((word) => ({
    text: word,
    type: word.trim() && !bSet.has(word) ? "removed" : "same",
  }));
  const bTokens: DiffToken[] = bWords.map((word) => ({
    text: word,
    type: word.trim() && !aSet.has(word) ? "added" : "same",
  }));

  return { aTokens, bTokens };
}

interface DiffToken {
  text: string;
  type: "same" | "added" | "removed";
}

function DiffText({ tokens }: { tokens: DiffToken[] }) {
  return (
    <p className="text-sm text-clay-200 whitespace-pre-wrap leading-relaxed">
      {tokens.map((token, i) => (
        <span
          key={i}
          className={cn(
            token.type === "removed" && "bg-red-500/20 text-red-300",
            token.type === "added" && "bg-emerald-500/20 text-emerald-300"
          )}
        >
          {token.text}
        </span>
      ))}
    </p>
  );
}

export function CompareDialog({
  open,
  onOpenChange,
  history,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  history: EmailLabRun[];
}) {
  const [leftId, setLeftId] = useState<string | null>(history[1]?.id ?? null);
  const [rightId, setRightId] = useState<string | null>(history[0]?.id ?? null);

  const leftRun = history.find((r) => r.id === leftId);
  const rightRun = history.find((r) => r.id === rightId);

  const diff = useMemo(() => {
    if (!leftRun || !rightRun) return null;
    return wordDiff(extractBody(leftRun), extractBody(rightRun));
  }, [leftRun, rightRun]);

  const formatLabel = (run: EmailLabRun) => {
    const company = (run.data.company_name as string) || run.skill;
    const time = new Date(run.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    return `${company} — ${run.model} @ ${time}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Compare Runs</DialogTitle>
        </DialogHeader>

        {/* Selectors */}
        <div className="grid grid-cols-2 gap-4 shrink-0">
          <Select value={leftId ?? ""} onValueChange={(v) => setLeftId(v || null)}>
            <SelectTrigger className="w-full" size="sm">
              <SelectValue placeholder="Select run..." />
            </SelectTrigger>
            <SelectContent>
              {history.map((run) => (
                <SelectItem key={run.id} value={run.id}>
                  {formatLabel(run)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={rightId ?? ""} onValueChange={(v) => setRightId(v || null)}>
            <SelectTrigger className="w-full" size="sm">
              <SelectValue placeholder="Select run..." />
            </SelectTrigger>
            <SelectContent>
              {history.map((run) => (
                <SelectItem key={run.id} value={run.id}>
                  {formatLabel(run)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Side by side */}
        {leftRun && rightRun && diff ? (
          <div className="grid grid-cols-2 gap-4 overflow-y-auto flex-1 min-h-0">
            {/* Left */}
            <div className="rounded-xl border border-clay-700 overflow-hidden">
              <div className="bg-clay-800/80 px-4 py-2 border-b border-clay-700">
                <p className="text-xs text-clay-300 font-medium truncate">
                  {extractSubject(leftRun) || "No subject"}
                </p>
              </div>
              <div className="px-4 py-3">
                <DiffText tokens={diff.aTokens} />
              </div>
            </div>
            {/* Right */}
            <div className="rounded-xl border border-clay-700 overflow-hidden">
              <div className="bg-clay-800/80 px-4 py-2 border-b border-clay-700">
                <p className="text-xs text-clay-300 font-medium truncate">
                  {extractSubject(rightRun) || "No subject"}
                </p>
              </div>
              <div className="px-4 py-3">
                <DiffText tokens={diff.bTokens} />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center py-12 text-clay-300 text-sm">
            Select two runs to compare
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
