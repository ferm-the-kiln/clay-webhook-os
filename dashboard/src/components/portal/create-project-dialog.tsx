"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Plus, X } from "lucide-react";
import { createProject } from "@/lib/api";
import { toast } from "sonner";

const COLOR_PALETTE = [
  "#6366f1", // indigo
  "#3b82f6", // blue
  "#06b6d4", // cyan
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#ec4899", // pink
  "#8b5cf6", // violet
];

interface CreateProjectDialogProps {
  slug: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}

export function CreateProjectDialog({ slug, open, onOpenChange, onCreated }: CreateProjectDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState(COLOR_PALETTE[0]);
  const [dueDate, setDueDate] = useState("");
  const [phases, setPhases] = useState<string[]>([]);
  const [newPhase, setNewPhase] = useState("");
  const [creating, setCreating] = useState(false);

  const handleAddPhase = () => {
    if (newPhase.trim()) {
      setPhases([...phases, newPhase.trim()]);
      setNewPhase("");
    }
  };

  const handleRemovePhase = (index: number) => {
    setPhases(phases.filter((_, i) => i !== index));
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error("Project name is required");
      return;
    }
    setCreating(true);
    try {
      await createProject(slug, {
        name: name.trim(),
        description: description.trim(),
        color,
        due_date: dueDate || undefined,
        phases: phases.length > 0
          ? phases.map((ph, i) => ({ name: ph, order: i }))
          : undefined,
      });
      toast.success(`Project "${name}" created`);
      setName("");
      setDescription("");
      setColor(COLOR_PALETTE[0]);
      setDueDate("");
      setPhases([]);
      onCreated();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create project");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-clay-800 border-clay-600 max-w-md">
        <DialogHeader>
          <DialogTitle className="text-clay-100">New Project</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {/* Name */}
          <div>
            <label className="text-xs font-medium text-clay-300 mb-1 block">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Q2 Outbound Campaign"
              className="w-full bg-clay-900 border border-clay-600 rounded-md px-3 py-2 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
              autoFocus
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-xs font-medium text-clay-300 mb-1 block">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this project about?"
              rows={2}
              className="w-full bg-clay-900 border border-clay-600 rounded-md px-3 py-2 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal resize-none"
            />
          </div>

          {/* Color */}
          <div>
            <label className="text-xs font-medium text-clay-300 mb-1 block">Color</label>
            <div className="flex gap-2">
              {COLOR_PALETTE.map((c) => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className="h-7 w-7 rounded-full border-2 transition-all"
                  style={{
                    backgroundColor: c,
                    borderColor: color === c ? "#fff" : "transparent",
                    transform: color === c ? "scale(1.15)" : "scale(1)",
                  }}
                />
              ))}
            </div>
          </div>

          {/* Target Date */}
          <div>
            <label className="text-xs font-medium text-clay-300 mb-1 block">
              Target Date <span className="text-clay-500">(optional)</span>
            </label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-full bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 focus:outline-none focus:border-kiln-teal"
            />
          </div>

          {/* Phases */}
          <div>
            <label className="text-xs font-medium text-clay-300 mb-1 block">
              Phases <span className="text-clay-500">(optional)</span>
            </label>
            {phases.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {phases.map((ph, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-clay-700 text-xs text-clay-200"
                  >
                    <span className="text-clay-500 text-[10px]">{i + 1}.</span>
                    {ph}
                    <button
                      onClick={() => handleRemovePhase(i)}
                      className="text-clay-500 hover:text-clay-300"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <input
                type="text"
                value={newPhase}
                onChange={(e) => setNewPhase(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddPhase())}
                placeholder="e.g. Discovery, Strategy, Execution"
                className="flex-1 bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddPhase}
                disabled={!newPhase.trim()}
                className="border-clay-600 text-clay-300 hover:bg-clay-700"
              >
                <Plus className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="border-clay-600 text-clay-300 hover:bg-clay-700"
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={creating || !name.trim()}
            className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90"
          >
            {creating ? "Creating..." : "Create Project"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
