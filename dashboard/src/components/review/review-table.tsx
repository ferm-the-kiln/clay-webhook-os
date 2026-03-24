"use client";

import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { OutputRenderer } from "@/components/output/output-renderer";
import { Check, X, Pencil, Undo2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { ReviewItem, ReviewStatus } from "@/hooks/use-review-queue";
import { toast } from "sonner";

interface ReviewTableProps {
  items: ReviewItem[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEdit: (id: string, output: Record<string, unknown>) => void;
}

const STATUS_BADGE: Record<ReviewStatus, { label: string; className: string }> = {
  pending: { label: "Pending", className: "bg-clay-500/20 text-clay-200" },
  approved: { label: "Approved", className: "bg-emerald-500/15 text-emerald-400" },
  edited: { label: "Edited", className: "bg-amber-500/15 text-amber-400" },
  rejected: { label: "Rejected", className: "bg-red-500/15 text-red-400" },
};

const ROW_BG: Record<ReviewStatus, string> = {
  pending: "",
  approved: "bg-emerald-500/5",
  edited: "bg-amber-500/5",
  rejected: "bg-red-500/5 opacity-60",
};

function truncate(val: unknown, max = 40): string {
  if (val == null) return "";
  const s = typeof val === "string" ? val : JSON.stringify(val);
  return s.length > max ? s.slice(0, max) + "..." : s;
}

function detectColumns(items: ReviewItem[]) {
  if (items.length === 0) return { inputCols: [], outputCols: [] };
  const first = items[0];
  const inputCols = Object.keys(first.input).slice(0, 3);
  const output = first.editedOutput || first.output;
  const outputCols = Object.keys(output)
    .filter((k) => !k.startsWith("_") && k !== "confidence_score" && k !== "overall_confidence_score")
    .slice(0, 3);
  return { inputCols, outputCols };
}

function ExpandedRow({
  item,
  onEdit,
  colSpan,
}: {
  item: ReviewItem;
  onEdit: (id: string, output: Record<string, unknown>) => void;
  colSpan: number;
}) {
  const [editing, setEditing] = useState(false);
  const [editJson, setEditJson] = useState("");
  const displayOutput = item.editedOutput || item.output;

  const handleStartEdit = () => {
    setEditJson(JSON.stringify(displayOutput, null, 2));
    setEditing(true);
  };

  const handleSaveEdit = () => {
    try {
      const parsed = JSON.parse(editJson);
      onEdit(item.id, parsed);
      setEditing(false);
    } catch {
      toast.error("Invalid JSON");
    }
  };

  return (
    <tr>
      <td colSpan={colSpan}>
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <div className="p-4 bg-clay-800/50 border-b border-clay-600">
            {/* Input details */}
            <div className="mb-3">
              <div className="text-[10px] font-medium text-clay-400 uppercase tracking-wider mb-1.5">
                Input
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(item.input).map(([key, val]) => (
                  <span
                    key={key}
                    className="text-[10px] text-clay-300 bg-clay-700 px-2 py-0.5 rounded"
                  >
                    <span className="font-mono">{key}:</span>{" "}
                    {String(val ?? "").slice(0, 80)}
                  </span>
                ))}
              </div>
            </div>

            {/* Output */}
            <div className="text-[10px] font-medium text-clay-400 uppercase tracking-wider mb-1.5 flex items-center gap-2">
              Output
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleStartEdit();
                }}
                className="text-clay-400 hover:text-clay-200 transition-colors"
                title="Edit output"
              >
                <Pencil className="h-3 w-3" />
              </button>
            </div>

            {editing ? (
              <div className="space-y-2">
                <Textarea
                  value={editJson}
                  onChange={(e) => setEditJson(e.target.value)}
                  rows={8}
                  className="font-mono text-xs bg-clay-900 border-clay-600"
                  onClick={(e) => e.stopPropagation()}
                />
                <div className="flex items-center gap-2 justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditing(false);
                    }}
                    className="text-clay-300 text-xs"
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSaveEdit();
                    }}
                    className="bg-kiln-teal text-clay-950 text-xs"
                  >
                    Save & Approve
                  </Button>
                </div>
              </div>
            ) : (
              <OutputRenderer result={displayOutput} />
            )}
          </div>
        </motion.div>
      </td>
    </tr>
  );
}

export function ReviewTable({ items, onApprove, onReject, onEdit }: ReviewTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { inputCols, outputCols } = useMemo(() => detectColumns(items), [items]);

  const colSpan = 1 + inputCols.length + outputCols.length + 2; // row# + inputs + outputs + status + actions

  if (items.length === 0) {
    return (
      <p className="text-xs text-clay-300 text-center py-8">
        No items match this filter
      </p>
    );
  }

  return (
    <div className="rounded-xl border border-clay-500 overflow-hidden">
      <div className="overflow-auto max-h-[600px]">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-10 bg-clay-800">
            <tr className="border-b border-clay-500">
              <th className="px-3 py-2 text-left text-[10px] font-medium text-clay-400 uppercase tracking-wider w-14">
                Row
              </th>
              {inputCols.map((col) => (
                <th
                  key={`in-${col}`}
                  className="px-3 py-2 text-left text-[10px] font-medium text-clay-400 uppercase tracking-wider"
                >
                  {col}
                </th>
              ))}
              {outputCols.map((col) => (
                <th
                  key={`out-${col}`}
                  className="px-3 py-2 text-left text-[10px] font-medium text-kiln-teal/70 uppercase tracking-wider"
                >
                  {col}
                </th>
              ))}
              <th className="px-3 py-2 text-left text-[10px] font-medium text-clay-400 uppercase tracking-wider w-24">
                Status
              </th>
              <th className="px-3 py-2 text-right text-[10px] font-medium text-clay-400 uppercase tracking-wider w-28">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const isExpanded = expandedId === item.id;
              const badge = STATUS_BADGE[item.reviewStatus];
              const output = item.editedOutput || item.output;

              return (
                <AnimatePresence key={item.id}>
                  <tr
                    onClick={() => setExpandedId(isExpanded ? null : item.id)}
                    className={cn(
                      "border-b border-clay-600 cursor-pointer transition-colors hover:bg-clay-800/50",
                      ROW_BG[item.reviewStatus],
                      isExpanded && "bg-clay-800/30"
                    )}
                  >
                    <td className="px-3 py-2 text-xs font-mono text-clay-300">
                      {item.rowIndex + 1}
                    </td>
                    {inputCols.map((col) => (
                      <td
                        key={`in-${col}`}
                        className="px-3 py-2 text-xs text-clay-200 max-w-[200px]"
                        title={String(item.input[col] ?? "")}
                      >
                        {truncate(item.input[col])}
                      </td>
                    ))}
                    {outputCols.map((col) => (
                      <td
                        key={`out-${col}`}
                        className="px-3 py-2 text-xs text-clay-200 max-w-[200px]"
                        title={typeof output[col] === "string" ? output[col] : JSON.stringify(output[col] ?? "")}
                      >
                        {truncate(output[col])}
                      </td>
                    ))}
                    <td className="px-3 py-2">
                      <Badge className={cn("text-[10px]", badge.className)}>
                        {badge.label}
                      </Badge>
                    </td>
                    <td className="px-3 py-2">
                      <div
                        className="flex items-center justify-end gap-0.5"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {item.reviewStatus !== "approved" &&
                          item.reviewStatus !== "edited" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => onApprove(item.id)}
                              className="h-6 w-6 p-0 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10"
                              title="Approve"
                            >
                              <Check className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        {item.reviewStatus !== "rejected" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onReject(item.id)}
                            className="h-6 w-6 p-0 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                            title="Reject"
                          >
                            <X className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        {(item.reviewStatus === "approved" ||
                          item.reviewStatus === "edited" ||
                          item.reviewStatus === "rejected") && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onApprove(item.id)}
                            className="h-6 w-6 p-0 text-clay-400 hover:text-clay-200"
                            title="Reset to pending"
                          >
                            <Undo2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {isExpanded && (
                    <ExpandedRow
                      item={item}
                      onEdit={onEdit}
                      colSpan={colSpan}
                    />
                  )}
                </AnimatePresence>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
