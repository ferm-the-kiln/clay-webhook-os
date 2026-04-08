"use client";

import { useState, useEffect } from "react";
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
import { Separator } from "@/components/ui/separator";
import { Copy, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { FunctionDefinition } from "@/lib/types";

interface FunctionSettingsPanelProps {
  open: boolean;
  onClose: () => void;
  func: FunctionDefinition;
  onSave: (fields: { name?: string; description?: string; folder?: string }) => Promise<void>;
  onDelete: () => Promise<void>;
  onDuplicate: () => Promise<void>;
}

export function FunctionSettingsPanel({
  open,
  onClose,
  func,
  onSave,
  onDelete,
  onDuplicate,
}: FunctionSettingsPanelProps) {
  const [name, setName] = useState(func.name);
  const [description, setDescription] = useState(func.description);
  const [folder, setFolder] = useState(func.folder);

  useEffect(() => {
    setName(func.name);
    setDescription(func.description);
    setFolder(func.folder);
  }, [func]);

  const handleSave = async () => {
    await onSave({ name, description, folder });
    onClose();
  };

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="w-[380px] bg-clay-950 border-clay-700 text-white overflow-y-auto"
      >
        <SheetHeader>
          <SheetTitle className="text-white">Function Settings</SheetTitle>
          <SheetDescription className="text-clay-300">
            {func.id}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-5">
          <div>
            <label className="text-xs text-clay-200">Name</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1.5 bg-clay-900 border-clay-500 text-white"
            />
          </div>

          <div>
            <label className="text-xs text-clay-200">Description</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1.5 bg-clay-900 border-clay-500 text-white min-h-[80px]"
            />
          </div>

          <div>
            <label className="text-xs text-clay-200">Folder</label>
            <Input
              value={folder}
              onChange={(e) => setFolder(e.target.value)}
              className="mt-1.5 bg-clay-900 border-clay-500 text-white"
            />
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1 border-clay-500 text-clay-100"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              className="flex-1 bg-kiln-teal text-black hover:bg-kiln-teal/90"
              onClick={handleSave}
            >
              Save
            </Button>
          </div>

          <Separator className="bg-clay-700" />

          {/* Info */}
          <div className="space-y-2 text-xs text-clay-300">
            <div className="flex justify-between">
              <span>Inputs</span>
              <span>{func.inputs.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Steps</span>
              <span>{func.steps.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Outputs</span>
              <span>{func.outputs.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Created</span>
              <span>{new Date(func.created_at * 1000).toLocaleDateString()}</span>
            </div>
          </div>

          <Separator className="bg-clay-700" />

          {/* Actions */}
          <div className="space-y-2">
            <Button
              variant="outline"
              className="w-full border-clay-500 text-clay-100 justify-start"
              onClick={() => {
                onDuplicate();
                onClose();
              }}
            >
              <Copy className="w-4 h-4 mr-2" />
              Duplicate Function
            </Button>
            <Button
              variant="outline"
              className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10 justify-start"
              onClick={() => {
                if (confirm("Delete this function? This cannot be undone.")) {
                  onDelete();
                }
              }}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Function
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
