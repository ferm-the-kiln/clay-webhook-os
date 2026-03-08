"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";

interface InlineEditorProps {
  content: string;
  onSave: (content: string) => void;
  onCancel: () => void;
}

export function InlineEditor({ content, onSave, onCancel }: InlineEditorProps) {
  const [value, setValue] = useState(content);
  const [hasChanges, setHasChanges] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setValue(content);
    setHasChanges(false);
  }, [content]);

  useEffect(() => {
    setHasChanges(value !== content);
  }, [value, content]);

  const handleSave = useCallback(() => {
    onSave(value);
    setHasChanges(false);
  }, [value, onSave]);

  // Cmd+S to save
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        if (hasChanges) handleSave();
      }
      if (e.key === "Escape") {
        onCancel();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [hasChanges, handleSave, onCancel]);

  const wordCount = value.split(/\s+/).filter(Boolean).length;
  const charCount = value.length;

  return (
    <div className="flex h-full flex-col">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="flex-1 w-full resize-none bg-transparent p-4 text-xs text-clay-200 font-mono leading-relaxed outline-none placeholder:text-clay-600"
        placeholder="Enter markdown content..."
        spellCheck={false}
      />
      <div className="flex items-center justify-between border-t border-clay-800 px-4 py-2">
        <div className="flex items-center gap-3 text-[10px] text-clay-600">
          <span>{wordCount} words</span>
          <span>{charCount} chars</span>
          {hasChanges && (
            <span className="flex items-center gap-1 text-amber-500">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              Unsaved
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onCancel}
            className="h-6 text-[10px] text-clay-500 hover:text-clay-300"
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges}
            className="h-6 text-[10px] bg-kiln-teal text-clay-950 hover:bg-kiln-teal/80 disabled:opacity-50"
          >
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}
