"use client";

import { X, Pencil, Trash2, Star, Copy, BookOpen, Users, TestTubes } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { FileNode } from "@/lib/types";
import { InlineEditor } from "./inline-editor";
import { toast } from "sonner";
import { motion } from "framer-motion";

interface FilePreviewPanelProps {
  file: FileNode | null;
  open: boolean;
  editMode: boolean;
  isFavorite: boolean;
  usageMap: Record<string, string[]>;
  onClose: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onToggleFavorite: () => void;
  onSave: (content: string) => void;
  onCancelEdit: () => void;
}

const DRIVE_LABELS: Record<string, { icon: typeof BookOpen; label: string }> = {
  "knowledge-base": { icon: BookOpen, label: "Knowledge Base" },
  clients: { icon: Users, label: "Clients" },
  skills: { icon: TestTubes, label: "Skills" },
};

export function FilePreviewPanel({
  file,
  open,
  editMode,
  isFavorite,
  usageMap,
  onClose,
  onEdit,
  onDelete,
  onToggleFavorite,
  onSave,
  onCancelEdit,
}: FilePreviewPanelProps) {
  if (!open || !file) return null;

  const driveInfo = DRIVE_LABELS[file.driveId];
  const DriveIcon = driveInfo?.icon || BookOpen;
  const usagePath = file.meta?.path as string | undefined;
  const skills = usagePath ? usageMap[usagePath] ?? [] : [];
  const wordCount = file.content
    ? file.content.split(/\s+/).filter(Boolean).length
    : 0;

  const copyPath = () => {
    const path = usagePath || `${file.driveId}/${file.name}`;
    navigator.clipboard.writeText(path);
    toast.success("Path copied");
  };

  return (
    <motion.div
      initial={{ x: 380, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 380, opacity: 0 }}
      transition={{ type: "spring", damping: 25, stiffness: 300 }}
      className="flex h-full w-[380px] shrink-0 flex-col border-l border-clay-800 bg-clay-950"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-clay-800 px-4 py-3">
        <div className="flex items-center gap-2 min-w-0">
          <DriveIcon className="h-4 w-4 shrink-0 text-kiln-teal" />
          <span className="text-sm font-medium text-clay-200 truncate">
            {file.name}
          </span>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-clay-500 hover:text-clay-300 hover:bg-clay-800 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Meta */}
      <div className="flex items-center gap-2 flex-wrap px-4 py-2 border-b border-clay-800/50">
        <Badge
          variant="outline"
          className="text-[10px] border-clay-700 text-clay-500"
        >
          {driveInfo?.label || file.driveId}
        </Badge>
        {file.category && (
          <Badge
            variant="outline"
            className="text-[10px] border-clay-700 text-clay-500"
          >
            {file.category}
          </Badge>
        )}
        {wordCount > 0 && (
          <span className="text-[10px] text-clay-600">{wordCount} words</span>
        )}
      </div>

      {/* Skills usage */}
      {skills.length > 0 && (
        <div className="px-4 py-2 border-b border-clay-800/50">
          <span className="text-[10px] text-clay-600 uppercase tracking-wider">
            Used by
          </span>
          <div className="flex flex-wrap gap-1 mt-1">
            {skills.map((s) => (
              <Badge
                key={s}
                variant="outline"
                className="text-[10px] border-kiln-teal/30 text-kiln-teal/70"
              >
                {s}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Action bar */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-clay-800/50">
        <Button
          variant="ghost"
          size="sm"
          onClick={onEdit}
          className="h-7 text-xs text-clay-400 hover:text-clay-200"
        >
          <Pencil className="h-3 w-3 mr-1" />
          {editMode ? "Preview" : "Edit"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleFavorite}
          className="h-7 text-xs text-clay-400 hover:text-clay-200"
        >
          <Star
            className={cn(
              "h-3 w-3 mr-1",
              isFavorite && "fill-amber-500 text-amber-500"
            )}
          />
          {isFavorite ? "Unpin" : "Pin"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={copyPath}
          className="h-7 text-xs text-clay-400 hover:text-clay-200"
        >
          <Copy className="h-3 w-3 mr-1" />
          Path
        </Button>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="sm"
          onClick={onDelete}
          className="h-7 text-xs text-kiln-coral hover:text-kiln-coral hover:bg-kiln-coral/10"
        >
          <Trash2 className="h-3 w-3 mr-1" />
          Delete
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {editMode && file.content !== undefined ? (
          <InlineEditor
            content={file.content}
            onSave={onSave}
            onCancel={onCancelEdit}
          />
        ) : (
          <div className="p-4">
            <pre className="whitespace-pre-wrap text-xs text-clay-300 font-mono leading-relaxed">
              {file.content || "No content available. Click Edit to add content."}
            </pre>
          </div>
        )}
      </div>
    </motion.div>
  );
}
