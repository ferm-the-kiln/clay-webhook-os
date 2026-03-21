"use client";

import { useState } from "react";
import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { updatePortal } from "@/lib/api";
import { toast } from "sonner";

interface InlineNotesProps {
  notes: string;
  slug: string;
  onSaved?: () => void;
}

export function InlineNotes({ notes, slug, onSaved }: InlineNotesProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(notes);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await updatePortal(slug, { notes: value });
      toast.success("Notes saved");
      setEditing(false);
      onSaved?.();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save notes");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-xl border border-clay-700 bg-clay-800 p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-clay-200">Internal Notes</h3>
        {!editing && (
          <button onClick={() => setEditing(true)} className="text-clay-500 hover:text-clay-300" title="Edit notes">
            <Pencil className="h-3 w-3" />
          </button>
        )}
      </div>
      {editing ? (
        <div className="space-y-2">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            rows={4}
            className="w-full rounded-md border border-clay-600 bg-clay-900 px-2.5 py-1.5 text-xs text-clay-100 placeholder:text-clay-500 focus:border-clay-400 focus:outline-none resize-none"
            placeholder="Add internal notes about this client..."
            autoFocus
          />
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={handleSave} disabled={saving} className="h-6 text-[11px] px-2">
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => { setValue(notes); setEditing(false); }} className="h-6 text-[11px] px-2 text-clay-400">
              Cancel
            </Button>
          </div>
        </div>
      ) : notes ? (
        <p className="text-xs text-clay-400 whitespace-pre-wrap">{notes}</p>
      ) : (
        <button onClick={() => setEditing(true)} className="text-xs text-clay-500 hover:text-clay-300 italic">
          No notes yet. Click to add.
        </button>
      )}
    </div>
  );
}
