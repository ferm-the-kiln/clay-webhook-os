"use client";

import { useState } from "react";
import { Plus, CheckCircle, Pencil, Trash2, Copy, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { PortalSOP } from "@/lib/types";
import { SOPEditor } from "./sop-editor";
import { TemplatePicker } from "./template-picker";
import { MarkdownContent } from "./markdown-content";
import { acknowledgeSOP } from "@/lib/api";
import { toast } from "sonner";

const CATEGORY_COLORS: Record<string, string> = {
  onboarding: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  reporting: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  communication: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  approval: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  general: "text-clay-300 bg-clay-700 border-clay-600",
};

interface SOPPillsProps {
  slug: string;
  sops: PortalSOP[];
  sopAcks: Record<string, { acknowledged_at: number; acknowledged_by: string }>;
  onCreated: () => void;
  onUpdated: () => void;
  onDelete: (sopId: string) => void;
}

export function SOPPills({ slug, sops, sopAcks = {}, onCreated, onUpdated, onDelete }: SOPPillsProps) {
  const [selectedSop, setSelectedSop] = useState<PortalSOP | null>(null);
  const [editing, setEditing] = useState(false);
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

  return (
    <>
      <div className="flex items-center gap-2 flex-wrap">
        <FileText className="h-4 w-4 text-clay-400 shrink-0" />
        {sops.map((sop) => {
          const acked = sop.id in sopAcks;
          const colors = CATEGORY_COLORS[sop.category] || CATEGORY_COLORS.general;
          return (
            <button
              key={sop.id}
              onClick={() => { setSelectedSop(sop); setEditing(false); }}
              className={cn(
                "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors hover:brightness-110",
                colors
              )}
            >
              {acked && <CheckCircle className="h-3 w-3 text-emerald-400" />}
              {sop.title}
            </button>
          );
        })}

        {/* New SOP pill */}
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-1 rounded-full border border-dashed border-clay-600 px-3 py-1 text-xs text-clay-400 hover:text-clay-200 hover:border-clay-400 transition-colors"
        >
          <Plus className="h-3 w-3" />
          New SOP
        </button>

        {/* Template button */}
        <button
          onClick={() => setTemplatePickerOpen(true)}
          className="flex items-center gap-1 rounded-full border border-dashed border-clay-600 px-3 py-1 text-xs text-clay-400 hover:text-clay-200 hover:border-clay-400 transition-colors"
        >
          <Copy className="h-3 w-3" />
          Template
        </button>
      </div>

      {/* SOP detail sheet */}
      <Sheet open={!!selectedSop && !editing} onOpenChange={(open) => { if (!open) setSelectedSop(null); }}>
        <SheetContent side="right" className="w-[440px] sm:w-[540px] bg-clay-900 border-clay-700">
          {selectedSop && (
            <>
              <SheetHeader>
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn(
                    "text-[10px] px-2 py-0.5 rounded-full font-medium",
                    CATEGORY_COLORS[selectedSop.category] || CATEGORY_COLORS.general
                  )}>
                    {selectedSop.category}
                  </span>
                  {selectedSop.id in sopAcks && (
                    <span className="flex items-center gap-1 text-[10px] text-emerald-400">
                      <CheckCircle className="h-3 w-3" />
                      Acknowledged
                    </span>
                  )}
                </div>
                <SheetTitle className="text-clay-100">{selectedSop.title}</SheetTitle>
              </SheetHeader>
              <div className="flex-1 overflow-y-auto py-4">
                <MarkdownContent content={selectedSop.content || "No content yet."} />
              </div>
              <SheetFooter className="flex-row gap-2 border-t border-clay-700 pt-4">
                {!(selectedSop.id in sopAcks) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleAck(selectedSop.id)}
                    className="text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10 gap-1.5"
                  >
                    <CheckCircle className="h-3.5 w-3.5" />
                    Mark as Read
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditing(true)}
                  className="text-clay-300 hover:text-clay-100 gap-1.5"
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => { onDelete(selectedSop.id); setSelectedSop(null); }}
                  className="text-red-400 hover:text-red-300 hover:bg-red-500/10 gap-1.5"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete
                </Button>
                <span className="ml-auto text-[10px] text-clay-500">
                  Updated {new Date(selectedSop.updated_at * 1000).toLocaleDateString()}
                </span>
              </SheetFooter>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* SOP editor sheet (for editing existing) */}
      <Sheet open={editing && !!selectedSop} onOpenChange={(open) => { if (!open) setEditing(false); }}>
        <SheetContent side="right" className="w-[440px] sm:w-[540px] bg-clay-900 border-clay-700">
          {selectedSop && (
            <div className="h-full flex flex-col">
              <SheetHeader>
                <SheetTitle className="text-clay-100">Edit SOP</SheetTitle>
              </SheetHeader>
              <div className="flex-1 overflow-y-auto py-4">
                <SOPEditor
                  slug={slug}
                  sop={selectedSop}
                  onSaved={() => { setEditing(false); setSelectedSop(null); onUpdated(); }}
                  onCancel={() => setEditing(false)}
                />
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* New SOP editor sheet */}
      <Sheet open={creating} onOpenChange={setCreating}>
        <SheetContent side="right" className="w-[440px] sm:w-[540px] bg-clay-900 border-clay-700">
          <div className="h-full flex flex-col">
            <SheetHeader>
              <SheetTitle className="text-clay-100">New SOP</SheetTitle>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto py-4">
              <SOPEditor
                slug={slug}
                onSaved={() => { setCreating(false); onCreated(); }}
                onCancel={() => setCreating(false)}
              />
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* Template picker dialog */}
      <TemplatePicker
        slug={slug}
        open={templatePickerOpen}
        onOpenChange={setTemplatePickerOpen}
        onCloned={onCreated}
      />
    </>
  );
}
