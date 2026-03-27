"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import {
  ArrowLeft,
  CopyPlus,
  FlaskConical,
  Play,
  Save,
  Pencil,
  Trash2,
  MessageSquareText,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import type { FunctionDefinition } from "@/lib/types";
import { explainFunction } from "@/lib/api";

interface FunctionHeaderProps {
  func: FunctionDefinition;
  editing: boolean;
  saving: boolean;
  testOpen: boolean;
  onToggleTest: () => void;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSave: () => void;
  onDelete: () => void;
  onDuplicate: () => void;
}

export function FunctionHeader({
  func,
  editing,
  saving,
  testOpen,
  onToggleTest,
  onEdit,
  onCancelEdit,
  onSave,
  onDelete,
  onDuplicate,
}: FunctionHeaderProps) {
  const router = useRouter();
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<{
    explanation: string;
    use_case: string;
    estimated_speed: string;
  } | null>(null);

  const handleExplain = async () => {
    setExplaining(true);
    try {
      const result = await explainFunction(func.id);
      setExplanation(result);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to explain function");
    } finally {
      setExplaining(false);
    }
  };

  return (
    <div className="mb-6 space-y-3">
      <div className="flex items-center justify-between">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => router.push("/")}
        className="text-clay-300 hover:text-clay-100"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back
      </Button>
      <div className="flex items-center gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExplain}
              disabled={explaining}
              className="border-clay-600 text-clay-300"
            >
              {explaining ? (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : (
                <MessageSquareText className="h-3.5 w-3.5 mr-1.5" />
              )}
              Explain
            </Button>
          </TooltipTrigger>
          <TooltipContent>AI explanation of what this function does</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleTest}
              className={cn(
                "border-clay-600 text-clay-300",
                testOpen && "border-kiln-teal text-kiln-teal"
              )}
            >
              <FlaskConical className="h-3.5 w-3.5 mr-1.5" />
              Quick Test
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <kbd className="text-[10px]">{"\u2318"}+Enter</kbd> to run
          </TooltipContent>
        </Tooltip>
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push(`/workbench?function=${func.id}`)}
          className="border-clay-600 text-clay-300"
        >
          <Play className="h-3.5 w-3.5 mr-1.5" />
          Run in Workbench
        </Button>
        {editing ? (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={onCancelEdit}
              className="border-clay-600 text-clay-300"
            >
              Cancel
            </Button>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="sm"
                  onClick={onSave}
                  disabled={saving}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
                >
                  <Save className="h-3.5 w-3.5 mr-1.5" />
                  {saving ? "Saving..." : "Save"}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <kbd className="text-[10px]">{"\u2318"}+S</kbd>
              </TooltipContent>
            </Tooltip>
          </>
        ) : (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={onDuplicate}
              className="border-clay-600 text-clay-300"
            >
              <CopyPlus className="h-3.5 w-3.5 mr-1.5" />
              Duplicate
            </Button>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="sm"
                  onClick={onEdit}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
                >
                  <Pencil className="h-3.5 w-3.5 mr-1.5" />
                  Edit
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <kbd className="text-[10px]">{"\u2318"}+E</kbd>
              </TooltipContent>
            </Tooltip>
            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              className="text-red-400 hover:text-red-300"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </>
        )}
      </div>
    </div>

    {/* Explanation banner */}
    {explanation && (
      <div className="bg-clay-900/50 border border-clay-700 rounded-lg p-3 flex items-start gap-3">
        <MessageSquareText className="h-4 w-4 text-kiln-teal shrink-0 mt-0.5" />
        <div className="flex-1 space-y-1">
          <p className="text-sm text-clay-100">{explanation.explanation}</p>
          <p className="text-xs text-clay-400">{explanation.use_case}</p>
          <span className={cn(
            "inline-block text-[10px] px-1.5 py-0.5 rounded",
            explanation.estimated_speed === "fast" ? "bg-emerald-500/15 text-emerald-400" :
            explanation.estimated_speed === "medium" ? "bg-amber-500/15 text-amber-400" :
            "bg-red-500/15 text-red-400"
          )}>
            {explanation.estimated_speed}
          </span>
        </div>
        <button onClick={() => setExplanation(null)} className="text-clay-500 hover:text-clay-300">
          <Trash2 className="h-3 w-3" />
        </button>
      </div>
    )}
    </div>
  );
}
