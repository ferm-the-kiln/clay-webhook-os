"use client";

import { useState } from "react";
import type { VariantDef } from "@/lib/types";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Save } from "lucide-react";

export function VariantEditor({
  open,
  onOpenChange,
  variant,
  saving,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  variant: VariantDef | null;
  saving: boolean;
  onSave: (label: string, content: string) => void;
}) {
  const [label, setLabel] = useState(variant?.label || "");
  const [content, setContent] = useState(variant?.content || "");

  // Reset form when variant changes
  useState(() => {
    setLabel(variant?.label || "");
    setContent(variant?.content || "");
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl bg-clay-900 border-clay-800 overflow-y-auto"
      >
        <SheetHeader>
          <SheetTitle className="text-kiln-cream">
            {variant ? "Edit Variant" : "New Variant"}
          </SheetTitle>
          <SheetDescription className="text-clay-500">
            {variant
              ? `Editing ${variant.id}`
              : "Create a new skill prompt variant"}
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-4 px-4 pb-4">
          <div>
            <label className="text-xs text-clay-500 uppercase tracking-wide mb-1.5 block">
              Label
            </label>
            <Input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g., Direct CTA variant"
              className="border-clay-700 bg-clay-950 text-clay-100 placeholder:text-clay-600"
            />
          </div>
          <div>
            <label className="text-xs text-clay-500 uppercase tracking-wide mb-1.5 block">
              Skill Prompt (Markdown)
            </label>
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="min-h-[400px] font-[family-name:var(--font-mono)] text-sm border-clay-700 bg-clay-950 text-clay-200 resize-y"
            />
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => onSave(label, content)}
              disabled={!label.trim() || !content.trim() || saving}
              className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
            >
              <Save className="h-4 w-4 mr-2" />
              {saving ? "Saving..." : "Save Variant"}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
