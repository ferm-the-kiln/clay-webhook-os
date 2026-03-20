"use client";

import { useState } from "react";
import type { ClientSummary, PromptPreview as PromptPreviewType } from "@/lib/types";
import { previewPrompt, fetchSkills } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Eye, FileText, Hash } from "lucide-react";
import { toast } from "sonner";
import { useEffect } from "react";

interface PromptPreviewProps {
  clients: ClientSummary[];
}

export function PromptPreview({ clients }: PromptPreviewProps) {
  const [skills, setSkills] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState("");
  const [selectedClient, setSelectedClient] = useState("");
  const [sampleData, setSampleData] = useState("{}");
  const [result, setResult] = useState<PromptPreviewType | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSkills()
      .then((res) => setSkills(res.skills))
      .catch(() => toast.error("Failed to load skills"));
  }, []);

  const handlePreview = async () => {
    if (!selectedSkill || !selectedClient) {
      toast.error("Select both a skill and a client");
      return;
    }
    setLoading(true);
    try {
      let parsed: Record<string, unknown> = {};
      try {
        parsed = JSON.parse(sampleData);
      } catch {
        toast.error("Invalid JSON in sample data");
        setLoading(false);
        return;
      }
      const res = await previewPrompt({
        skill: selectedSkill,
        client_slug: selectedClient,
        sample_data: Object.keys(parsed).length > 0 ? parsed : undefined,
      });
      setResult(res);
    } catch (e) {
      toast.error("Preview failed", { description: (e as Error).message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-clay-200 mb-1 block">
            Skill
          </label>
          <Select value={selectedSkill} onValueChange={setSelectedSkill}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select a skill..." />
            </SelectTrigger>
            <SelectContent>
              {skills.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-xs font-medium text-clay-200 mb-1 block">
            Client
          </label>
          <Select value={selectedClient} onValueChange={setSelectedClient}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select a client..." />
            </SelectTrigger>
            <SelectContent>
              {clients.map((c) => (
                <SelectItem key={c.slug} value={c.slug}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-clay-200 mb-1 block">
          Sample Data (optional JSON)
        </label>
        <Textarea
          value={sampleData}
          onChange={(e) => setSampleData(e.target.value)}
          rows={3}
          className="font-mono resize-y"
          placeholder='{"first_name": "Sarah", "company_name": "Acme"}'
        />
      </div>

      <Button
        onClick={handlePreview}
        disabled={loading || !selectedSkill || !selectedClient}
        className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        ) : (
          <Eye className="h-4 w-4 mr-2" />
        )}
        Preview Prompt
      </Button>

      {result && (
        <div className="space-y-4 mt-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-sm text-clay-200">
              <Hash className="h-3.5 w-3.5" />
              <span>~{result.estimated_tokens.toLocaleString()} tokens</span>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-clay-200">
              <FileText className="h-3.5 w-3.5" />
              <span>{result.context_files_loaded.length} context files</span>
            </div>
          </div>

          {result.context_files_loaded.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.context_files_loaded.map((f) => (
                <Badge
                  key={f}
                  variant="secondary"
                  className="bg-clay-800 text-clay-300 border-clay-700 text-xs font-mono"
                >
                  {f}
                </Badge>
              ))}
            </div>
          )}

          <Card className="bg-clay-800 border-clay-500 p-0">
            <pre className="p-4 text-xs text-clay-300 font-mono whitespace-pre-wrap break-words max-h-[500px] overflow-auto">
              {result.assembled_prompt}
            </pre>
          </Card>
        </div>
      )}
    </div>
  );
}
