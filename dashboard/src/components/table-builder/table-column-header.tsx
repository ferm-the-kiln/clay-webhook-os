"use client";

import {
  Search,
  Brain,
  Calculator,
  Filter,
  Pencil,
  Type,
  MoreVertical,
  Trash2,
  ArrowUp,
  ArrowDown,
  Play,
  RotateCcw,
  Pin,
  EyeOff,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { motion } from "framer-motion";
import type { TableColumn } from "@/lib/types";
import type { ColumnProgress } from "@/hooks/use-table-builder";

const TYPE_ICONS: Record<string, typeof Search> = {
  enrichment: Search,
  ai: Brain,
  formula: Calculator,
  gate: Filter,
  input: Pencil,
  static: Type,
};

const TYPE_ICON_COLORS: Record<string, string> = {
  enrichment: "text-blue-400",
  ai: "text-purple-400",
  formula: "text-teal-400",
  gate: "text-amber-400",
  input: "text-zinc-500",
  static: "text-zinc-500",
};

interface TableColumnHeaderProps {
  column: TableColumn;
  progress?: ColumnProgress;
  onDelete: () => void;
  onSort: () => void;
  sortDir: "asc" | "desc" | null;
}

export function TableColumnHeader({
  column,
  progress,
  onDelete,
  onSort,
  sortDir,
}: TableColumnHeaderProps) {
  const Icon = TYPE_ICONS[column.column_type] || Type;
  const iconColor = TYPE_ICON_COLORS[column.column_type] || "text-zinc-500";

  const hasProgress = progress && progress.total > 0;
  const percent = hasProgress ? Math.round((progress.done / progress.total) * 100) : 0;
  const errorPercent = hasProgress
    ? Math.round((progress.errors / progress.total) * 100)
    : 0;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 group">
        <Icon className={`w-3 h-3 shrink-0 ${iconColor}`} />
        <span className="truncate flex-1 text-zinc-300 font-medium">
          {column.name}
        </span>
        {sortDir === "asc" && <ArrowUp className="w-3 h-3 text-kiln-teal" />}
        {sortDir === "desc" && <ArrowDown className="w-3 h-3 text-kiln-teal" />}

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-zinc-700 transition-opacity">
              <MoreVertical className="w-3 h-3 text-zinc-500" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="bg-zinc-900 border-zinc-700 text-sm">
            <DropdownMenuItem onClick={onSort} className="text-zinc-300">
              {sortDir === "asc" ? (
                <ArrowDown className="w-3 h-3 mr-2" />
              ) : (
                <ArrowUp className="w-3 h-3 mr-2" />
              )}
              Sort {sortDir === "asc" ? "Z-A" : "A-Z"}
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-zinc-700" />
            <DropdownMenuItem
              onClick={onDelete}
              className="text-red-400 focus:text-red-400"
            >
              <Trash2 className="w-3 h-3 mr-2" />
              Delete column
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Tri-color progress bar */}
      {hasProgress && (
        <div className="flex items-center gap-1.5">
          <div className="flex-1 h-1 rounded-full bg-zinc-800 overflow-hidden">
            <motion.div
              className="h-full flex"
              initial={{ width: 0 }}
              animate={{ width: "100%" }}
            >
              {/* Green = done */}
              <div
                className="bg-emerald-500 h-full"
                style={{ width: `${percent - errorPercent}%` }}
              />
              {/* Red = errors */}
              {errorPercent > 0 && (
                <div
                  className="bg-red-500 h-full"
                  style={{ width: `${errorPercent}%` }}
                />
              )}
            </motion.div>
          </div>
          <span className="text-[10px] text-zinc-500 tabular-nums w-7 text-right">
            {percent}%
          </span>
        </div>
      )}
    </div>
  );
}
