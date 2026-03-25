"use client";

import { useState, useRef, useEffect } from "react";
import { Plus, CheckCircle, Pencil, Trash2, Copy, FileText, ChevronDown } from "lucide-react";
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
  const [popoverOpen, setPopoverOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close popover on outside click
  useEffect(() => {
    if (!popoverOpen) return;
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setPopoverOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [popoverOpen]);

  const handleAck = async (sopId: string) => {
    try {
      await acknowledgeSOP(slug, sopId, "team");
      toast.success("SOP acknowledged");
      onUpdated();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to acknowledge SOP");
    }
  };

  // Hide entirely when no SOPs
  if (sops.length === 0) return null;

  return (
    <>
      {/* Compact trigger with popover */}
      <div className="relative" ref={popoverRef}>
        <button
          onClick={() => setPopoverOpen(!popoverOpen)}
          className="flex items-center gap-1.5 text-xs font-medium text-clay-300 hover:text-clay-100 transition-colors px-2.5 py-1.5 rounded-lg border border-clay-700 bg-clay-800/60 hover:bg-clay-800"
        >
          <FileText className="h-3.5 w-3.5 text-clay-400" />
          {sops.length} {sops.length === 1 ? "SOP" : "SOPs"}
          <ChevronDown className={cn("h-3 w-3 text-clay-500 transition-transform", popoverOpen && "rotate-180")} />
        </button>

        {popoverOpen && (
          <div className="absolute top-full left-0 mt-1.5 z-30 w-64 rounded-lg border border-clay-700 bg-clay-900 shadow-xl animate-in fade-in slide-in-from-top-1 duration-150">
            <div className="p-2 space-y-1">
              {sops.map((sop) => {
                const acked = sop.id in sopAcks;
                const colors = CATEGORY_COLORS[sop.category] || CATEGORY_COLORS.general;
                return (
                  <button
                    key={sop.id}
                    onClick={() => { setSelectedSop(sop); setEditing(false); setPopoverOpen(false); }}
                    className="w-full flex items-center gap-2 rounded-md px-2.5 py-2 text-xs text-clay-200 hover:bg-clay-800 transition-colors text-left"
                  >
                    <span className={cn("h-2 w-2 rounded-full shrink-0", CATEGORY_COLORS[sop.category]?.split(" ")[0]?.replace("text-", "bg-") || "bg-clay-400")} />
                    <span className="truncate flex-1">{sop.title}</span>
                    {acked && <CheckCircle className="h-3 w-3 text-emerald-400 shrink-0" />}
                  </button>
                );
              })}
            </div>
            <div className="border-t border-clay-700 p-2 flex items-center gap-1.5">
              <button
                onClick={() => { setCreating(true); setPopoverOpen(false); }}
                className="flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs text-clay-400 hover:text-clay-200 hover:bg-clay-800 transition-colors flex-1"
              >
                <Plus className="h-3 w-3" />
                New SOP
              </button>
              <button
                onClick={() => { setTemplatePickerOpen(true); setPopoverOpen(false); }}
                className="flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs text-clay-400 hover:text-clay-200 hover:bg-clay-800 transition-colors flex-1"
              >
                <Copy className="h-3 w-3" />
                Template
              </button>
            </div>
          </div>
        )}
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
