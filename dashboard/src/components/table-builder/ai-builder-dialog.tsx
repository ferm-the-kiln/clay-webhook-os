"use client";

import { useState } from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import {
  Sparkles,
  X,
  Loader2,
  Search,
  Brain,
  Calculator,
  Filter,
  Pencil,
  Type,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { assembleTableColumns } from "@/lib/api";

interface AiBuilderDialogProps {
  open: boolean;
  onClose: () => void;
  onApplyColumns: (
    tableName: string,
    columns: Array<{
      name: string;
      id: string;
      column_type: string;
      tool?: string;
      params?: Record<string, string>;
      ai_prompt?: string;
      ai_model?: string;
      condition?: string;
      formula?: string;
    }>,
  ) => void;
}

const TYPE_ICONS: Record<string, typeof Search> = {
  input: Pencil,
  enrichment: Search,
  ai: Brain,
  formula: Calculator,
  gate: Filter,
  static: Type,
};

const TYPE_COLORS: Record<string, string> = {
  input: "text-clay-200 bg-clay-700",
  enrichment: "text-blue-400 bg-blue-500/10",
  ai: "text-purple-400 bg-purple-500/10",
  formula: "text-teal-400 bg-teal-500/10",
  gate: "text-amber-400 bg-amber-500/10",
  static: "text-clay-200 bg-clay-700",
};

const EXAMPLE_PROMPTS = [
  "Find people with VP/Director titles at target companies, qualify them, then write personalized emails",
  "Research companies via web search, extract key metrics with AI, and score their fit",
  "Find email addresses for a list of contacts and verify deliverability",
  "Enrich company data from domains, identify decision makers, and draft LinkedIn messages",
];

export function AiBuilderDialog({
  open,
  onClose,
  onApplyColumns,
}: AiBuilderDialogProps) {
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    table_name: string;
    columns: Array<{
      name: string;
      id: string;
      column_type: string;
      tool?: string;
      params?: Record<string, string>;
      ai_prompt?: string;
      ai_model?: string;
      condition?: string;
      formula?: string;
    }>;
  } | null>(null);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await assembleTableColumns({ description: description.trim() });
      setResult({ table_name: res.table_name, columns: res.columns });
    } catch {
      setError("Failed to generate columns. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (!result) return;
    onApplyColumns(result.table_name, result.columns);
    onClose();
    // Reset state
    setDescription("");
    setResult(null);
    setError("");
  };

  const handleClose = () => {
    onClose();
    setDescription("");
    setResult(null);
    setError("");
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 bg-black/60 z-50" />
        <DialogPrimitive.Content className="fixed top-[10%] left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 bg-clay-900 border border-clay-500 rounded-xl shadow-2xl overflow-hidden max-h-[80vh] flex flex-col">
          <DialogPrimitive.Title className="sr-only">AI Table Builder</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">
            Describe what you want to achieve and AI will build the columns
          </DialogPrimitive.Description>

          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-clay-700">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-purple-400" />
              </div>
              <span className="text-sm font-medium text-white">AI Table Builder</span>
            </div>
            <button onClick={handleClose} className="text-clay-300 hover:text-clay-100">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="overflow-y-auto flex-1 p-5 space-y-4">
            {/* Input section */}
            {!result && (
              <>
                <div>
                  <label className="text-xs text-clay-200 mb-2 block">
                    What are you trying to achieve?
                  </label>
                  <Textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g., Find people with VP/Director titles at my target companies, qualify them based on company size and industry, then write personalized outreach emails..."
                    className="bg-clay-700 border-clay-500 text-white min-h-[100px] text-sm"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && e.metaKey) handleGenerate();
                    }}
                  />
                </div>

                {/* Example prompts */}
                <div>
                  <label className="text-[10px] text-clay-300 uppercase tracking-wider mb-2 block">
                    Examples
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {EXAMPLE_PROMPTS.map((ex, i) => (
                      <button
                        key={i}
                        onClick={() => setDescription(ex)}
                        className="text-left text-[11px] text-clay-300 hover:text-clay-100 px-3 py-2 rounded-lg border border-clay-700 hover:border-clay-500 transition-colors"
                      >
                        {ex}
                      </button>
                    ))}
                  </div>
                </div>

                {error && (
                  <p className="text-xs text-red-400">{error}</p>
                )}
              </>
            )}

            {/* Loading state */}
            {loading && (
              <div className="flex flex-col items-center justify-center py-12 gap-3">
                <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
                <p className="text-sm text-clay-200">Building your table columns...</p>
                <p className="text-xs text-clay-300">This takes about 10-20 seconds</p>
              </div>
            )}

            {/* Result: column preview */}
            {result && !loading && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-white">{result.table_name}</h3>
                  <span className="text-xs text-clay-300">
                    {result.columns.length} columns
                  </span>
                </div>

                {/* Column chain visualization */}
                <div className="space-y-1.5">
                  {result.columns.map((col, i) => {
                    const Icon = TYPE_ICONS[col.column_type] || Type;
                    const colorClass = TYPE_COLORS[col.column_type] || TYPE_COLORS.input;
                    return (
                      <div
                        key={col.id}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-clay-700 bg-clay-700/30"
                      >
                        <span className="text-[10px] text-clay-300 font-mono w-4 shrink-0">
                          {i + 1}
                        </span>
                        <div className={`w-6 h-6 rounded flex items-center justify-center shrink-0 ${colorClass}`}>
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-medium text-clay-100">{col.name}</div>
                          <div className="text-[11px] text-clay-300 truncate">
                            {col.column_type === "enrichment" && col.tool
                              ? `Tool: ${col.tool}`
                              : col.column_type === "ai"
                                ? `AI: ${(col.ai_prompt || "").slice(0, 60)}...`
                                : col.column_type === "gate"
                                  ? `Gate: ${col.condition}`
                                  : col.column_type === "formula"
                                    ? `Formula: ${col.formula}`
                                    : "User-provided data"}
                          </div>
                        </div>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${colorClass}`}>
                          {col.column_type}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Regenerate option */}
                <button
                  onClick={() => {
                    setResult(null);
                    setError("");
                  }}
                  className="text-xs text-clay-300 hover:text-clay-100 mt-3 underline"
                >
                  Back to edit prompt
                </button>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-clay-700 bg-clay-950/50">
            <Button
              variant="outline"
              size="sm"
              className="border-clay-500 text-clay-100 h-8"
              onClick={handleClose}
            >
              Cancel
            </Button>
            {!result ? (
              <Button
                size="sm"
                className="bg-purple-600 text-white hover:bg-purple-500 h-8"
                onClick={handleGenerate}
                disabled={loading || !description.trim()}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    Building...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3 h-3 mr-1" />
                    Build Columns
                  </>
                )}
              </Button>
            ) : (
              <Button
                size="sm"
                className="bg-kiln-teal text-black hover:bg-kiln-teal/90 h-8"
                onClick={handleApply}
              >
                <Check className="w-3 h-3 mr-1" />
                Create Table with {result.columns.length} Columns
              </Button>
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
