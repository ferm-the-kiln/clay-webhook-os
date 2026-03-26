"use client";

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
  Monitor,
  Cloud,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { isLocalExecutionMode } from "@/lib/api";
import type { FunctionDefinition } from "@/lib/types";

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

  return (
    <div className="flex items-center justify-between mb-6">
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
        {/* Execution mode indicator */}
        <Tooltip>
          <TooltipTrigger asChild>
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-full border",
                isLocalExecutionMode()
                  ? "bg-violet-500/10 text-violet-400 border-violet-500/25"
                  : "bg-sky-500/10 text-sky-400 border-sky-500/25"
              )}
            >
              {isLocalExecutionMode() ? (
                <Monitor className="h-3 w-3" />
              ) : (
                <Cloud className="h-3 w-3" />
              )}
              {isLocalExecutionMode() ? "Local" : "Remote"}
            </span>
          </TooltipTrigger>
          <TooltipContent>
            {isLocalExecutionMode()
              ? "Executing via local claude CLI — consolidated prompts, fewer calls"
              : "Executing via remote backend (VPS)"}
          </TooltipContent>
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
  );
}
