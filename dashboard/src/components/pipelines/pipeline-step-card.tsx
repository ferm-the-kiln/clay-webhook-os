"use client";

import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { PipelineStepConfig } from "@/lib/types";
import { MODELS } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { GripVertical, Settings2, Trash2, ChevronDown, ChevronUp } from "lucide-react";

export function PipelineStepCard({
  step,
  index,
  id,
  onChange,
  onRemove,
}: {
  step: PipelineStepConfig;
  index: number;
  id: string;
  onChange: (updated: PipelineStepConfig) => void;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rounded-lg border bg-clay-900 p-3 ${
        isDragging
          ? "border-kiln-teal/50 bg-clay-800 shadow-lg z-10"
          : "border-clay-800"
      }`}
    >
      <div className="flex items-center gap-2">
        <button
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-clay-600 hover:text-clay-400"
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <Badge
          variant="outline"
          className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 text-xs font-mono"
        >
          {index + 1}
        </Badge>
        <span className="font-medium text-clay-200 flex-1">{step.skill}</span>
        {(step.model || step.instructions) && (
          <Settings2 className="h-3 w-3 text-kiln-mustard" />
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-clay-500 hover:text-clay-200"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? (
            <ChevronUp className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-clay-500 hover:text-kiln-coral"
          onClick={onRemove}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-clay-800 space-y-3">
          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              Model Override
            </label>
            <Select
              value={step.model || "default"}
              onValueChange={(v) =>
                onChange({ ...step, model: v === "default" ? null : v })
              }
            >
              <SelectTrigger className="border-clay-700 bg-clay-950 text-clay-200 h-8 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-clay-700 bg-clay-900">
                <SelectItem value="default">Pipeline default</SelectItem>
                {MODELS.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              Step Instructions
            </label>
            <Textarea
              value={step.instructions || ""}
              onChange={(e) =>
                onChange({
                  ...step,
                  instructions: e.target.value || null,
                })
              }
              placeholder="Optional instructions for this step..."
              className="h-16 border-clay-700 bg-clay-950 text-clay-200 placeholder:text-clay-600 text-sm resize-none"
            />
          </div>
        </div>
      )}
    </div>
  );
}
