"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Save, X } from "lucide-react";
import { createAction, updateAction } from "@/lib/api";
import type { PortalAction, ActionOwner, ActionPriority, ActionRecurrence } from "@/lib/types";
import { toast } from "sonner";

const OWNERS = [
  { id: "internal", label: "Internal" },
  { id: "client", label: "Client" },
];

const PRIORITIES = [
  { id: "high", label: "High" },
  { id: "normal", label: "Normal" },
  { id: "low", label: "Low" },
];

const RECURRENCES = [
  { id: "none", label: "No repeat" },
  { id: "weekly", label: "Weekly" },
  { id: "biweekly", label: "Biweekly" },
  { id: "monthly", label: "Monthly" },
];

interface ActionEditorProps {
  slug: string;
  action?: PortalAction;
  onSaved: () => void;
  onCancel: () => void;
}

export function ActionEditor({ slug, action, onSaved, onCancel }: ActionEditorProps) {
  const [title, setTitle] = useState(action?.title || "");
  const [description, setDescription] = useState(action?.description || "");
  const [owner, setOwner] = useState<ActionOwner>(action?.owner || "internal");
  const [priority, setPriority] = useState<ActionPriority>(action?.priority || "normal");
  const [dueDate, setDueDate] = useState(action?.due_date || "");
  const [recurrence, setRecurrence] = useState<ActionRecurrence>(action?.recurrence || "none");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!title.trim()) {
      toast.error("Title is required");
      return;
    }
    setSaving(true);
    try {
      if (action) {
        await updateAction(slug, action.id, {
          title,
          description,
          owner,
          priority,
          due_date: dueDate || null,
          recurrence: recurrence === "none" ? null : recurrence,
        });
        toast.success("Action updated");
      } else {
        await createAction(slug, {
          title,
          description,
          owner,
          priority,
          due_date: dueDate || null,
          recurrence: recurrence === "none" ? undefined : recurrence,
        });
        toast.success("Action created");
      }
      onSaved();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save action");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-kiln-teal/30 bg-clay-800 p-4 space-y-3">
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Action item title..."
        className="w-full bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
        autoFocus
      />

      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Details (optional)..."
        rows={3}
        className="w-full bg-clay-900 border border-clay-600 rounded-md px-3 py-2 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal resize-y"
      />

      <div className="flex gap-3">
        <select
          value={owner}
          onChange={(e) => setOwner(e.target.value as ActionOwner)}
          className="bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 focus:outline-none focus:border-kiln-teal"
        >
          {OWNERS.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>

        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as ActionPriority)}
          className="bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 focus:outline-none focus:border-kiln-teal"
        >
          {PRIORITIES.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          className="bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 focus:outline-none focus:border-kiln-teal"
        />

        <select
          value={recurrence}
          onChange={(e) => setRecurrence(e.target.value as ActionRecurrence)}
          className="bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 focus:outline-none focus:border-kiln-teal"
        >
          {RECURRENCES.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2 justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={onCancel}
          className="text-clay-300 hover:text-clay-100 gap-1.5"
        >
          <X className="h-3.5 w-3.5" />
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={handleSave}
          disabled={saving || !title.trim()}
          className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90 gap-1.5"
        >
          <Save className="h-3.5 w-3.5" />
          {saving ? "Saving..." : action ? "Update" : "Create"}
        </Button>
      </div>
    </div>
  );
}
