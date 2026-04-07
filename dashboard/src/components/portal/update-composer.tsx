"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Send, FileText, Loader2, Paperclip, X, FileIcon, Image, Bold, Italic, Link, List, Eye, EyeOff, Info } from "lucide-react";
import { createPortalUpdate, fetchUpdateTemplates, uploadPortalMedia, deletePortalMedia } from "@/lib/api";
import { toast } from "sonner";
import type { UpdateTemplate, PortalMedia, ProjectSummary } from "@/lib/types";
import { AuthorPicker, getSelectedAuthor, saveAuthor } from "./author-picker";
import { MarkdownContent } from "./markdown-content";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const UPDATE_TYPES = [
  { id: "update", label: "Update" },
  { id: "milestone", label: "Milestone" },
  { id: "deliverable", label: "Deliverable" },
  { id: "note", label: "Note" },
];

interface UpdateComposerProps {
  slug: string;
  clientName?: string;
  projectId?: string;
  projects?: ProjectSummary[];
  onPosted: () => void;
}

export function UpdateComposer({ slug, clientName, projectId: initialProjectId, projects, onPosted }: UpdateComposerProps) {
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
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>(initialProjectId);
  const [showPreview, setShowPreview] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bodyRef = useRef<HTMLTextAreaElement>(null);

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
        project_id: selectedProjectId ?? undefined,
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
      className={`rounded-lg border bg-clay-850 p-5 space-y-4 retro-raised transition-colors ${
        dragOver ? "border-kiln-teal bg-kiln-teal/5" : "border-clay-700/60"
      }`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Author row */}
      <div className="flex items-center gap-3 pb-4 border-b border-clay-700/40">
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
            className={`text-sm px-3.5 py-1.5 transition-colors ${
              authorOrg === "internal"
                ? "bg-kiln-teal/15 text-kiln-teal"
                : "bg-clay-800 text-clay-400 hover:text-clay-200"
            }`}
          >
            {internalLabel}
          </button>
          <button
            onClick={() => setAuthorOrg("client")}
            className={`text-sm px-3.5 py-1.5 border-l border-clay-600 transition-colors ${
              authorOrg === "client"
                ? "bg-purple-500/15 text-purple-400"
                : "bg-clay-800 text-clay-400 hover:text-clay-200"
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
              className={`text-sm px-3.5 py-1.5 rounded-full transition-colors ${
                type === t.id
                  ? "bg-kiln-teal/15 text-kiln-teal border border-kiln-teal/30"
                  : "bg-clay-700 text-clay-300 border border-clay-600/60 hover:border-clay-500"
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

      {/* Project selector (shown when projects available and not pre-locked to a project) */}
      {projects && projects.length > 0 && !initialProjectId && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-clay-500">Project:</span>
          <select
            value={selectedProjectId || ""}
            onChange={(e) => setSelectedProjectId(e.target.value || undefined)}
            className="bg-clay-900 border border-clay-600 rounded-md px-2.5 py-1 text-xs text-clay-200 focus:outline-none focus:border-kiln-teal appearance-none cursor-pointer"
          >
            <option value="">None</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Title your update..."
        className="w-full bg-clay-900/80 border border-clay-600/80 rounded-lg px-3.5 py-3 text-lg font-semibold text-clay-100 placeholder:text-clay-400/60 focus:outline-none focus:border-kiln-teal"
      />

      {/* Markdown toolbar + preview toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-0.5">
          {[
            { icon: Bold, insert: "**", wrap: true, title: "Bold" },
            { icon: Italic, insert: "_", wrap: true, title: "Italic" },
            { icon: Link, insert: "[text](url)", wrap: false, title: "Link" },
            { icon: List, insert: "- ", wrap: false, title: "List" },
          ].map(({ icon: Icon, insert, wrap, title: btnTitle }) => (
            <button
              key={btnTitle}
              onClick={() => {
                const ta = bodyRef.current;
                if (!ta) return;
                const start = ta.selectionStart;
                const end = ta.selectionEnd;
                const selected = body.substring(start, end);
                if (wrap && selected) {
                  const newText = body.substring(0, start) + insert + selected + insert + body.substring(end);
                  setBody(newText);
                  setTimeout(() => { ta.focus(); ta.setSelectionRange(start + insert.length, end + insert.length); }, 0);
                } else {
                  const newText = body.substring(0, start) + insert + body.substring(end);
                  setBody(newText);
                  setTimeout(() => { ta.focus(); ta.setSelectionRange(start + insert.length, start + insert.length); }, 0);
                }
              }}
              className="h-7 w-7 rounded flex items-center justify-center text-clay-400 hover:text-clay-200 hover:bg-clay-700 transition-colors"
              title={btnTitle}
            >
              <Icon className="h-3.5 w-3.5" />
            </button>
          ))}
        </div>
        <button
          onClick={() => setShowPreview(!showPreview)}
          className="flex items-center gap-1 text-[11px] text-clay-400 hover:text-clay-200 transition-colors"
        >
          {showPreview ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
          {showPreview ? "Edit" : "Preview"}
        </button>
      </div>

      {/* Body textarea or preview */}
      <div className="relative">
        {showPreview ? (
          <div className="min-h-[80px] bg-clay-900/80 border border-clay-600/80 rounded-lg px-3.5 py-2.5">
            {body ? (
              <MarkdownContent content={body} />
            ) : (
              <p className="text-sm text-clay-500">Nothing to preview</p>
            )}
          </div>
        ) : (
          <textarea
            ref={bodyRef}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Add details (supports **markdown**)..."
            rows={3}
            className="w-full bg-clay-900/80 border border-clay-600/80 rounded-lg px-3.5 py-2.5 text-sm text-clay-100 placeholder:text-clay-400 focus:outline-none focus:border-kiln-teal resize-y"
          />
        )}
        {body && !showPreview && (
          <span className="absolute bottom-2 right-3 text-[10px] text-clay-500">
            {body.trim().split(/\s+/).filter(Boolean).length} words
          </span>
        )}
      </div>

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
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs text-clay-300 cursor-pointer">
            <input
              type="checkbox"
              checked={createAction}
              onChange={(e) => setCreateAction(e.target.checked)}
              className="accent-kiln-teal"
            />
            Auto-create client review action
          </label>
          {createAction && (
            <div className="flex items-center gap-2 text-[11px] text-purple-400/70 bg-purple-500/5 border border-purple-500/10 rounded-lg px-3 py-2">
              <Info className="h-3.5 w-3.5 shrink-0" />
              A review action will be created for the client with an approval workflow
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-between pt-4 border-t border-clay-700/40">
        {/* Attach button */}
        <label className="flex items-center gap-1.5 text-sm text-clay-300 hover:text-clay-200 cursor-pointer transition-colors">
          <Paperclip className="h-4 w-4" />
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
