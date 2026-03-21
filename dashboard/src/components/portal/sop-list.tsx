"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Plus, Pencil, Trash2, Copy, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { PortalSOP } from "@/lib/types";
import { SOPEditor } from "./sop-editor";
import { TemplatePicker } from "./template-picker";
import { MarkdownContent } from "./markdown-content";
import { acknowledgeSOP } from "@/lib/api";
import { toast } from "sonner";

const CATEGORY_COLORS: Record<string, string> = {
  onboarding: "text-blue-400 bg-blue-500/10",
  reporting: "text-emerald-400 bg-emerald-500/10",
  communication: "text-purple-400 bg-purple-500/10",
  approval: "text-amber-400 bg-amber-500/10",
  general: "text-clay-300 bg-clay-700",
};

interface SOPListProps {
  slug: string;
  sops: PortalSOP[];
  sopAcks?: Record<string, { acknowledged_at: number; acknowledged_by: string }>;
  onCreated: () => void;
  onUpdated: () => void;
  onDelete: (sopId: string) => void;
}

export function SOPList({ slug, sops, sopAcks = {}, onCreated, onUpdated, onDelete }: SOPListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [templatePickerOpen, setTemplatePickerOpen] = useState(false);

  const handleAck = async (sopId: string) => {
    try {
      await acknowledgeSOP(slug, sopId, "team");
      toast.success("SOP acknowledged");
      onUpdated();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to acknowledge SOP");
    }
  };

  const ackedCount = sops.filter((s) => s.id in sopAcks).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-clay-200">
            Standard Operating Procedures ({sops.length})
          </h3>
          {sops.length > 0 && (
            <p className="text-[10px] text-clay-500 mt-0.5">
              {ackedCount} of {sops.length} acknowledged
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setTemplatePickerOpen(true)}
            className="border-clay-600 text-clay-200 hover:bg-clay-700 gap-1.5"
          >
            <Copy className="h-3.5 w-3.5" />
            From Template
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCreating(true)}
            className="border-clay-600 text-clay-200 hover:bg-clay-700 gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" />
            New SOP
          </Button>
        </div>
      </div>

      <TemplatePicker
        slug={slug}
        open={templatePickerOpen}
        onOpenChange={setTemplatePickerOpen}
        onCloned={onCreated}
      />

      {creating && (
        <SOPEditor
          slug={slug}
          onSaved={() => {
            setCreating(false);
            onCreated();
          }}
          onCancel={() => setCreating(false)}
        />
      )}

      {sops.length === 0 && !creating && (
        <div className="text-center py-8 text-clay-400">
          <p className="text-sm">No SOPs yet. Create your first one to define expectations.</p>
        </div>
      )}

      {sops.map((sop) => {
        const ack = sopAcks[sop.id];
        return (
          <div key={sop.id} className="rounded-lg border border-clay-700 bg-clay-800 overflow-hidden">
            {editingId === sop.id ? (
              <SOPEditor
                slug={slug}
                sop={sop}
                onSaved={() => {
                  setEditingId(null);
                  onUpdated();
                }}
                onCancel={() => setEditingId(null)}
              />
            ) : (
              <>
                <button
                  onClick={() => setExpandedId(expandedId === sop.id ? null : sop.id)}
                  className="w-full flex items-center gap-3 p-3 text-left hover:bg-clay-750 transition-colors"
                >
                  {expandedId === sop.id ? (
                    <ChevronDown className="h-4 w-4 text-clay-400 shrink-0" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-clay-400 shrink-0" />
                  )}
                  <span className="flex-1 text-sm font-medium text-clay-100">{sop.title}</span>
                  {ack && (
                    <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-medium shrink-0">
                      <CheckCircle className="h-3 w-3" />
                      Acknowledged
                    </span>
                  )}
                  <span
                    className={cn(
                      "text-[10px] px-2 py-0.5 rounded-full font-medium",
                      CATEGORY_COLORS[sop.category] || CATEGORY_COLORS.general
                    )}
                  >
                    {sop.category}
                  </span>
                </button>
                {expandedId === sop.id && (
                  <div className="border-t border-clay-700 p-4">
                    <MarkdownContent content={sop.content || "No content yet."} className="mb-3" />
                    <div className="flex items-center gap-2 pt-2 border-t border-clay-700">
                      {!ack && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleAck(sop.id)}
                          className="text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10 gap-1.5 h-7"
                        >
                          <CheckCircle className="h-3 w-3" />
                          Mark as Read
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setEditingId(sop.id)}
                        className="text-clay-300 hover:text-clay-100 gap-1.5 h-7"
                      >
                        <Pencil className="h-3 w-3" />
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDelete(sop.id)}
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10 gap-1.5 h-7"
                      >
                        <Trash2 className="h-3 w-3" />
                        Delete
                      </Button>
                      <span className="ml-auto text-[10px] text-clay-500">
                        Updated {new Date(sop.updated_at * 1000).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
