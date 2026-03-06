"use client";

import type { SkillAnalytics } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function ApprovalBar({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-clay-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            pct >= 70 ? "bg-kiln-teal" : pct >= 40 ? "bg-kiln-mustard" : "bg-kiln-coral"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-clay-400 font-[family-name:var(--font-mono)] w-10 text-right">
        {pct}%
      </span>
    </div>
  );
}

export function SkillPerformanceTable({
  skills,
}: {
  skills: SkillAnalytics[];
}) {
  if (skills.length === 0) {
    return (
      <p className="text-sm text-clay-500 py-8 text-center">
        No feedback data yet. Rate some outputs to see skill performance.
      </p>
    );
  }

  const sorted = [...skills].sort((a, b) => b.total - a.total);

  return (
    <div className="rounded-xl border border-clay-800 bg-clay-900 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="border-clay-800 hover:bg-transparent">
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide">
              Skill
            </TableHead>
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide text-right">
              Ratings
            </TableHead>
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide text-right">
              Up
            </TableHead>
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide text-right">
              Down
            </TableHead>
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide w-48">
              Approval
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((s) => (
            <TableRow
              key={s.skill}
              className="border-clay-800 hover:bg-clay-800/50"
            >
              <TableCell className="text-kiln-teal font-medium">
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
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
