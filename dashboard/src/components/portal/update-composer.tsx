"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Send, FileText, Loader2 } from "lucide-react";
import { createPortalUpdate, fetchUpdateTemplates } from "@/lib/api";
import { toast } from "sonner";
import type { UpdateTemplate } from "@/lib/types";

const UPDATE_TYPES = [
  { id: "update", label: "Update" },
  { id: "milestone", label: "Milestone" },
  { id: "deliverable", label: "Deliverable" },
  { id: "note", label: "Note" },
];

interface UpdateComposerProps {
  slug: string;
  onPosted: () => void;
}

export function UpdateComposer({ slug, onPosted }: UpdateComposerProps) {
  const [type, setType] = useState("update");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [createAction, setCreateAction] = useState(true);
  const [posting, setPosting] = useState(false);
  const [templates, setTemplates] = useState<UpdateTemplate[]>([]);
  const [templateMenuOpen, setTemplateMenuOpen] = useState(false);

  // Restore draft from localStorage on mount
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(`portal-draft-${slug}`);
      if (raw) {
        const draft = JSON.parse(raw);
        if (draft.type) setType(draft.type);
        if (draft.title) setTitle(draft.title);
        if (draft.body) setBody(draft.body);
      }
    } catch { /* ignore */ }
  }, [slug]);

  // Auto-save draft (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        if (title || body) {
          localStorage.setItem(`portal-draft-${slug}`, JSON.stringify({ type, title, body }));
        } else {
          localStorage.removeItem(`portal-draft-${slug}`);
        }
      } catch { /* ignore */ }
    }, 500);
    return () => clearTimeout(timer);
  }, [slug, type, title, body]);

  useEffect(() => {
    fetchUpdateTemplates()
      .then((res) => setTemplates(res.templates))
      .catch(() => {});
  }, []);

  const handlePost = async () => {
    if (!title.trim()) {
      toast.error("Title is required");
      return;
    }
    setPosting(true);
    try {
      await createPortalUpdate(slug, {
        type,
        title,
        body,
        create_action: type === "deliverable" && createAction,
      });
      toast.success("Update posted");
      setTitle("");
      setBody("");
      setType("update");
      try { localStorage.removeItem(`portal-draft-${slug}`); } catch { /* ignore */ }
      onPosted();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to post update");
    } finally {
      setPosting(false);
    }
  };

  const applyTemplate = (template: UpdateTemplate) => {
    setType(template.type);
    setTitle(template.title);
    setBody(template.body);
    setTemplateMenuOpen(false);
    toast.success(`Template "${template.title}" applied`);
  };

  return (
    <div className="rounded-lg border border-clay-600 bg-clay-800 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {UPDATE_TYPES.map((t) => (
            <button
              key={t.id}
              onClick={() => setType(t.id)}
              className={`text-xs px-3 py-1 rounded-full transition-colors ${
                type === t.id
                  ? "bg-kiln-teal/15 text-kiln-teal border border-kiln-teal/30"
                  : "bg-clay-700 text-clay-300 border border-clay-600 hover:border-clay-500"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {templates.length > 0 && (
          <div className="relative">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setTemplateMenuOpen(!templateMenuOpen)}
              className="border-clay-600 text-clay-300 hover:text-clay-100 hover:bg-clay-700 gap-1.5 h-7 text-xs"
            >
              <FileText className="h-3 w-3" />
              Template
            </Button>

            {templateMenuOpen && (
              <div className="absolute right-0 top-full mt-1 w-56 rounded-lg border border-clay-600 bg-clay-800 shadow-xl z-20 py-1">
                {templates.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => applyTemplate(t)}
                    className="w-full text-left px-3 py-2 text-xs text-clay-200 hover:bg-clay-700 transition-colors"
                  >
                    <span className="font-medium">{t.title}</span>
                    <span className="block text-[10px] text-clay-500 mt-0.5">{t.type}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="What happened?"
        className="w-full bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
      />

      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Add details (supports **markdown**)..."
        rows={3}
        className="w-full bg-clay-900 border border-clay-600 rounded-md px-3 py-2 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal resize-y"
      />

      {type === "deliverable" && (
        <label className="flex items-center gap-2 text-xs text-clay-300 cursor-pointer">
          <input
            type="checkbox"
            checked={createAction}
            onChange={(e) => setCreateAction(e.target.checked)}
            className="accent-kiln-teal"
          />
          Auto-create client review action
        </label>
      )}

      <div className="flex justify-end">
        <Button
          size="sm"
          onClick={handlePost}
          disabled={posting || !title.trim()}
          className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90 gap-1.5"
        >
          {posting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Send className="h-3.5 w-3.5" />
          )}
          {posting ? "Posting..." : "Post Update"}
        </Button>
      </div>
    </div>
  );
}
