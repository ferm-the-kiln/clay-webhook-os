"use client";

import { useState } from "react";
import { previewPrompt } from "@/lib/api";
import { formatTokens } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Eye, FileText, Loader2 } from "lucide-react";

export function PromptDrawer({
  skill,
  json,
}: {
  skill: string;
  json: string;
}) {
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState<string | null>(null);
  const [contextFiles, setContextFiles] = useState<string[]>([]);
  const [tokens, setTokens] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpen = async (isOpen: boolean) => {
    setOpen(isOpen);
    if (!isOpen || !skill) return;

    setLoading(true);
    setError(null);
    try {
      let sampleData: Record<string, unknown> = {};
      try {
        sampleData = JSON.parse(json);
      } catch {
        // use empty data if JSON is invalid
      }
      const clientSlug = (sampleData.client_slug as string) || "";
      const res = await previewPrompt({
        skill,
        client_slug: clientSlug,
        sample_data: sampleData,
      });
      setPrompt(res.assembled_prompt);
      setContextFiles(res.context_files_loaded);
      setTokens(res.estimated_tokens);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={handleOpen}>
      <SheetTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={!skill}
          className="border-clay-700 bg-clay-900 text-clay-300 hover:bg-clay-800 hover:text-clay-100"
        >
          <Eye className="h-3.5 w-3.5 mr-1.5" />
          View Prompt
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full sm:max-w-2xl bg-clay-950 border-clay-800 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-clay-100">Assembled Prompt</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-4">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-kiln-teal" />
            </div>
          )}
          {error && (
            <p className="text-sm text-kiln-coral">{error}</p>
          )}
          {!loading && !error && prompt && (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="outline" className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30">
                  ~{formatTokens(tokens)} tokens
                </Badge>
                {contextFiles.map((f) => (
                  <Badge
                    key={f}
                    variant="outline"
                    className="bg-clay-900 text-clay-400 border-clay-700"
                  >
                    <FileText className="h-3 w-3 mr-1" />
                    {f}
                  </Badge>
                ))}
              </div>
              <pre className="rounded-lg border border-clay-800 bg-clay-900 p-4 text-sm text-clay-200 font-[family-name:var(--font-mono)] whitespace-pre-wrap break-words overflow-auto max-h-[70vh]">
                {prompt}
              </pre>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
