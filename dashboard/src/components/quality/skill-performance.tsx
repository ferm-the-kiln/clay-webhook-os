"use client";

import { useState } from "react";
import type { SkillAnalytics } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

type SortKey = "skill" | "total" | "thumbs_up" | "thumbs_down" | "approval_rate";
type SortDir = "asc" | "desc";

function ApprovalBar({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-clay-800 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            pct >= 70
              ? "bg-kiln-teal"
              : pct >= 50
                ? "bg-kiln-mustard"
                : "bg-kiln-coral"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-clay-200 font-[family-name:var(--font-mono)] w-10 text-right">
        {pct}%
      </span>
    </div>
  );
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <ArrowUpDown className="h-3 w-3 text-clay-400" />;
  return dir === "asc" ? (
    <ArrowUp className="h-3 w-3 text-kiln-teal" />
  ) : (
    <ArrowDown className="h-3 w-3 text-kiln-teal" />
  );
}

export function SkillPerformance({ skills }: { skills: SkillAnalytics[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("total");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  if (skills.length === 0) {
    return (
      <p className="text-sm text-clay-200 py-8 text-center">
        No feedback data yet. Rate some outputs to see skill performance.
      </p>
    );
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "skill" ? "asc" : "desc");
    }
  };

  const sorted = [...skills].sort((a, b) => {
    const mul = sortDir === "asc" ? 1 : -1;
    if (sortKey === "skill") return mul * a.skill.localeCompare(b.skill);
    return mul * ((a[sortKey] as number) - (b[sortKey] as number));
  });

  const columns: { key: SortKey; label: string; align?: "right" }[] = [
    { key: "skill", label: "Skill" },
    { key: "total", label: "Total Feedback", align: "right" },
    { key: "thumbs_up", label: "Thumbs Up", align: "right" },
    { key: "thumbs_down", label: "Thumbs Down", align: "right" },
    { key: "approval_rate", label: "Approval %" },
  ];

  return (
    <div className="rounded-xl border border-clay-500 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="border-clay-500 hover:bg-transparent">
            {columns.map((col) => (
              <TableHead
                key={col.key}
                className={cn(
                  "text-clay-200 text-xs uppercase tracking-wider cursor-pointer select-none hover:text-clay-100 transition-colors",
                  col.align === "right" && "text-right",
                  col.key === "approval_rate" && "w-48"
                )}
                onClick={() => handleSort(col.key)}
              >
                <span className="inline-flex items-center gap-1">
                  {col.label}
                  <SortIcon active={sortKey === col.key} dir={sortDir} />
                </span>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((s) => {
            const approvalPct = Math.round(s.approval_rate * 100);
            const belowThreshold = approvalPct < 70;

            return (
              <TableRow
                key={s.skill}
                className={cn(
                  "border-clay-500 hover:bg-muted/50 transition-colors",
                  belowThreshold && "bg-kiln-coral/5"
                )}
              >
                <TableCell
                  className={cn(
                    "font-medium",
                    belowThreshold ? "text-kiln-coral" : "text-kiln-teal"
                  )}
                >
                  {s.skill}
                </TableCell>
                <TableCell className="text-clay-300 text-right font-[family-name:var(--font-mono)] text-sm">
                  {s.total}
                </TableCell>
                <TableCell className="text-kiln-teal text-right font-[family-name:var(--font-mono)] text-sm">
                  {s.thumbs_up}
                </TableCell>
                <TableCell className="text-kiln-coral text-right font-[family-name:var(--font-mono)] text-sm">
                  {s.thumbs_down}
                </TableCell>
                <TableCell>
                  <ApprovalBar rate={s.approval_rate} />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
