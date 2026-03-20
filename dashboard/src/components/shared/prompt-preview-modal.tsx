"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Eye, X, Loader2, Copy, Check, FileText, Zap } from "lucide-react";
import { previewPrompt } from "@/lib/api";

export function PromptPreviewButton({
  skill,
  dataJson,
  className,
}: {
  skill: string;
  dataJson: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [contextFiles, setContextFiles] = useState<string[]>([]);
  const [estimatedTokens, setEstimatedTokens] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleOpen = async () => {
    setOpen(true);
    setLoading(true);
    setError(null);
    setPrompt("");
    setContextFiles([]);
    setEstimatedTokens(0);

    try {
      let parsed: Record<string, unknown> = {};
      try {
        parsed = JSON.parse(dataJson);
      } catch {
        // empty data
      }

      const result = await previewPrompt({
        skill,
        client_slug: (parsed.client_slug as string) ?? "",
        sample_data: parsed,
      });

      setPrompt(result.assembled_prompt ?? JSON.stringify(result, null, 2));
      setContextFiles(result.context_files_loaded ?? []);
      setEstimatedTokens(result.estimated_tokens ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load prompt preview");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleOpen}
        className={cn("text-xs text-clay-300 hover:text-kiln-teal h-7", className)}
      >
        <Eye className="h-3.5 w-3.5 mr-1" />
        See what AI sees
      </Button>

      {/* Modal overlay */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />

          {/* Modal */}
          <div className="relative w-full max-w-3xl max-h-[80vh] mx-4 rounded-xl border border-clay-700 bg-clay-900 shadow-2xl flex flex-col overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-clay-700 bg-clay-800/50">
              <div>
                <h2 className="text-sm font-semibold text-clay-100">
                  Prompt Preview
                </h2>
                <p className="text-[11px] text-clay-300 mt-0.5">
                  This is everything the AI knows when writing your email
                </p>
              </div>
              <div className="flex items-center gap-1">
                {prompt && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopy}
                    className="h-7 text-xs text-clay-300 hover:text-clay-100"
                  >
                    {copied ? (
                      <Check className="h-3.5 w-3.5 mr-1 text-emerald-400" />
                    ) : (
                      <Copy className="h-3.5 w-3.5 mr-1" />
                    )}
                    {copied ? "Copied" : "Copy"}
                  </Button>
                )}
                <button
                  onClick={() => setOpen(false)}
                  className="h-7 w-7 flex items-center justify-center rounded-md text-clay-300 hover:text-clay-100 hover:bg-clay-700/50"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-4">
              {loading && (
                <div className="flex items-center justify-center py-12 text-clay-300">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  <span className="text-sm">Assembling prompt...</span>
                </div>
              )}
              {error && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}
              {prompt && (
                <>
                  {/* Context summary */}
                  {(contextFiles.length > 0 || estimatedTokens > 0) && (
                    <div className="mb-4 rounded-lg border border-clay-700 bg-clay-800/40 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-1.5 text-xs font-medium text-clay-200">
                          <FileText className="h-3.5 w-3.5 text-kiln-teal" />
                          Context Files ({contextFiles.length})
                        </div>
                        {estimatedTokens > 0 && (
                          <div className="flex items-center gap-1.5 text-xs text-clay-300">
                            <Zap className="h-3 w-3" />
                            ~{estimatedTokens.toLocaleString()} tokens
                          </div>
                        )}
                      </div>
                      <div className="font-[family-name:var(--font-mono)] text-[11px] text-clay-300 space-y-0.5">
                        {contextFiles.map((file, i) => (
                          <div key={file} className="flex items-start">
                            <span className="text-clay-300 mr-1.5 select-none">
                              {i === contextFiles.length - 1 ? "└──" : "├──"}
                            </span>
                            <span className="text-clay-300">{file}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <pre className="text-xs text-clay-200 font-[family-name:var(--font-mono)] whitespace-pre-wrap leading-relaxed">
                    {prompt}
                  </pre>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
