"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Send, FileText, Loader2, Paperclip, X, FileIcon, Image } from "lucide-react";
import { createPortalUpdate, fetchUpdateTemplates, uploadPortalMedia, deletePortalMedia } from "@/lib/api";
import { toast } from "sonner";
import type { UpdateTemplate, PortalMedia } from "@/lib/types";
import { AuthorPicker, getSelectedAuthor, saveAuthor } from "./author-picker";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";

const UPDATE_TYPES = [
  { id: "update", label: "Update" },
  { id: "milestone", label: "Milestone" },
  { id: "deliverable", label: "Deliverable" },
  { id: "note", label: "Note" },
];

interface UpdateComposerProps {
  slug: string;
  clientName?: string;
  onPosted: () => void;
}

export function UpdateComposer({ slug, clientName, onPosted }: UpdateComposerProps) {
  const [type, setType] = useState("update");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [authorName, setAuthorName] = useState("");
  const [authorOrg, setAuthorOrg] = useState<"internal" | "client">("internal");
  const [createAction, setCreateAction] = useState(true);
  const [posting, setPosting] = useState(false);
  const [templates, setTemplates] = useState<UpdateTemplate[]>([]);
  const [templateMenuOpen, setTemplateMenuOpen] = useState(false);
  const [pendingMedia, setPendingMedia] = useState<PortalMedia[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Restore draft from localStorage on mount + load saved author
  useEffect(() => {
    if (typeof window === "undefined") return;
    const lastAuthor = getSelectedAuthor();
    if (lastAuthor) setAuthorName(lastAuthor);
    try {
      const raw = localStorage.getItem(`portal-draft-${slug}`);
      if (raw) {
        const draft = JSON.parse(raw);
        if (draft.type) setType(draft.type);
        if (draft.title) setTitle(draft.title);
        if (draft.body) setBody(draft.body);
        if (draft.authorName) setAuthorName(draft.authorName);
        if (draft.authorOrg) setAuthorOrg(draft.authorOrg);
      }
    } catch { /* ignore */ }
  }, [slug]);

  // Auto-save draft (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        if (title || body || authorName) {
          localStorage.setItem(`portal-draft-${slug}`, JSON.stringify({ type, title, body, authorName, authorOrg }));
        } else {
          localStorage.removeItem(`portal-draft-${slug}`);
        }
      } catch { /* ignore */ }
    }, 500);
    return () => clearTimeout(timer);
  }, [slug, type, title, body, authorName, authorOrg]);

  useEffect(() => {
    fetchUpdateTemplates()
      .then((res) => setTemplates(res.templates))
      .catch(() => {});
  }, []);

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    setUploading(true);
    const uploads = Array.from(files).map(async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("caption", "");
      try {
        const media = await uploadPortalMedia(slug, formData);
        setPendingMedia((prev) => [...prev, media]);
      } catch (e) {
        toast.error(`Failed to upload ${file.name}`);
      }
    });
    await Promise.allSettled(uploads);
    setUploading(false);
  }, [slug]);

  const removeMedia = useCallback(async (mediaId: string) => {
    try {
      await deletePortalMedia(slug, mediaId);
      setPendingMedia((prev) => prev.filter((m) => m.id !== mediaId));
    } catch {
      toast.error("Failed to remove file");
    }
  }, [slug]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  const handlePost = async () => {
    if (!authorName.trim()) {
      toast.error("Name is required");
      return;
    }
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
        media_ids: pendingMedia.map((m) => m.id),
        create_action: type === "deliverable" && createAction,
        author_name: authorName,
        author_org: authorOrg,
      });
      toast.success("Update posted");
      setTitle("");
      setBody("");
      setType("update");
      setPendingMedia([]);
      saveAuthor(authorName);
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

  const internalLabel = "The Kiln";
  const clientLabel = clientName || "Client";

  return (
    <div
      className={`rounded-lg border bg-clay-800 p-4 space-y-3 transition-colors ${
        dragOver ? "border-kiln-teal bg-kiln-teal/5" : "border-clay-600"
      }`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Author row */}
      <div className="flex items-center gap-3">
        <AuthorPicker
          value={authorName}
          onChange={(name) => { setAuthorName(name); saveAuthor(name); }}
          size="md"
          placeholder="Select name"
          className="flex-1"
        />
        <div className="flex rounded-md border border-clay-600 overflow-hidden shrink-0">
          <button
            onClick={() => setAuthorOrg("internal")}
            className={`text-xs px-3 py-1.5 transition-colors ${
              authorOrg === "internal"
                ? "bg-kiln-teal/15 text-kiln-teal"
                : "bg-clay-900 text-clay-400 hover:text-clay-200"
            }`}
          >
            {internalLabel}
          </button>
          <button
            onClick={() => setAuthorOrg("client")}
            className={`text-xs px-3 py-1.5 border-l border-clay-600 transition-colors ${
              authorOrg === "client"
                ? "bg-purple-500/15 text-purple-400"
                : "bg-clay-900 text-clay-400 hover:text-clay-200"
            }`}
          >
            {clientLabel}
          </button>
        </div>
      </div>

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

      {/* Pending media preview strip */}
      {(pendingMedia.length > 0 || uploading) && (
        <div className="flex flex-wrap gap-2">
          {pendingMedia.map((m) => {
            const isImg = m.mime_type.startsWith("image/");
            const fullUrl = `${API_URL}${m.url}`;
            return (
              <div
                key={m.id}
                className="relative group/media flex items-center gap-2 rounded-md bg-clay-900 border border-clay-700 px-2 py-1.5"
              >
                {isImg ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={fullUrl}
                    alt={m.original_name}
                    className="h-10 w-10 rounded object-cover"
                  />
                ) : (
                  <FileIcon className="h-4 w-4 text-clay-500 shrink-0" />
                )}
                <span className="text-xs text-clay-300 max-w-[120px] truncate">
                  {m.original_name}
                </span>
                <button
                  onClick={() => removeMedia(m.id)}
                  className="opacity-0 group-hover/media:opacity-100 absolute -top-1.5 -right-1.5 h-4 w-4 rounded-full bg-clay-700 border border-clay-600 flex items-center justify-center transition-opacity"
                >
                  <X className="h-2.5 w-2.5 text-clay-300" />
                </button>
              </div>
            );
          })}
          {uploading && (
            <div className="flex items-center gap-1.5 px-2 py-1.5 text-xs text-clay-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Uploading...
            </div>
          )}
        </div>
      )}

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

      <div className="flex items-center justify-between">
        {/* Attach button */}
        <label className="flex items-center gap-1.5 text-xs text-clay-400 hover:text-clay-200 cursor-pointer transition-colors">
          <Paperclip className="h-3.5 w-3.5" />
          <span>Attach</span>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            accept="image/*,video/*,.pdf,.doc,.docx,.xls,.xlsx,.pptx,.csv,.txt"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                handleFiles(e.target.files);
                e.target.value = "";
              }
            }}
          />
        </label>

        <Button
          size="sm"
          onClick={handlePost}
          disabled={posting || uploading || !authorName.trim() || !title.trim()}
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
