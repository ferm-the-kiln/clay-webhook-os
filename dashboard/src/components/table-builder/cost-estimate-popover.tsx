"use client";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DollarSign } from "lucide-react";
import type { TableDefinition } from "@/lib/types";

interface CostEstimatePopoverProps {
  table: TableDefinition;
  rowCount: number;
  limit?: number;
  children: React.ReactNode;
}

export function CostEstimatePopover({
  table,
  rowCount,
  limit,
  children,
}: CostEstimatePopoverProps) {
  const enrichCols = table.columns.filter(
    (c) => c.column_type === "enrichment" || c.column_type === "ai",
  );
  const rows = limit ? Math.min(limit, rowCount) : rowCount;
  const totalCalls = enrichCols.length * rows;
  const estimatedCost = totalCalls * 0.03; // ~$0.03 per sonnet call

  if (enrichCols.length === 0 || rows === 0) {
    return <>{children}</>;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent
        side="bottom"
        className="bg-zinc-900 border-zinc-700 text-xs p-3 max-w-64"
      >
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-zinc-300 font-medium">
            <DollarSign className="w-3 h-3 text-amber-400" />
            Execution Estimate
          </div>
          <div className="text-zinc-400">
            {enrichCols.length} column{enrichCols.length > 1 ? "s" : ""} x{" "}
            {rows} row{rows > 1 ? "s" : ""} ={" "}
            <span className="text-white">{totalCalls} AI calls</span>
          </div>
          <div className="text-zinc-500">
            ~${estimatedCost.toFixed(2)} estimated (Sonnet)
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
