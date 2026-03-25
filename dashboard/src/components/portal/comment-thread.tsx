"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { MessageCircle, Send, Trash2, Loader2, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchComments, postComment, deleteComment } from "@/lib/api";
import { MarkdownContent } from "./markdown-content";
import { toast } from "sonner";
import type { PortalComment } from "@/lib/types";
import { AuthorPicker, getSelectedAuthor, saveAuthor } from "./author-picker";

interface CommentThreadProps {
  slug: string;
  updateId: string;
  initialCount?: number;
}

export function CommentThread({ slug, updateId, initialCount = 0 }: CommentThreadProps) {
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState<PortalComment[]>([]);
  const [loading, setLoading] = useState(false);
  const [body, setBody] = useState("");
  const [author, setAuthor] = useState("");
  const [posting, setPosting] = useState(false);
  const [count, setCount] = useState(initialCount);
  const [changingAuthor, setChangingAuthor] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load last selected author on mount
  useEffect(() => {
    const last = getSelectedAuthor();
    if (last) setAuthor(last);
  }, []);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetchComments(slug, updateId)
      .then((res) => {
        setComments(res.comments);
        setCount(res.total);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [slug, updateId, open]);

  const autoGrow = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 96) + "px";
  }, []);

  const handlePost = async () => {
    if (!body.trim() || !author.trim()) {
      toast.error("Select a name and write a comment");
      return;
    }
    setPosting(true);
    try {
      const comment = await postComment(slug, updateId, { body, author });
      setComments((prev) => [...prev, comment]);
      setCount((c) => c + 1);
      setBody("");
      saveAuthor(author);
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
      toast.success("Comment posted");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to post comment");
    } finally {
      setPosting(false);
    }
  };

  const handleDelete = async (commentId: string) => {
    try {
      await deleteComment(slug, updateId, commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      setCount((c) => c - 1);
      toast.success("Comment deleted");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete comment");
    }
  };

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs text-clay-300 hover:text-clay-100 transition-colors"
      >
        <MessageCircle className="h-3.5 w-3.5" />
        {count > 0 ? (
          <>
            <span className="min-w-[1.25rem] h-5 px-1 rounded-full bg-kiln-teal/15 text-kiln-teal text-[10px] font-semibold inline-flex items-center justify-center">
              {count}
            </span>
            <span>comment{count !== 1 ? "s" : ""}</span>
          </>
        ) : "Comment"}
      </button>

      {open && (
        <div className="mt-3 space-y-3 border-t border-clay-700 pt-3">
          {loading ? (
            <div className="flex items-center gap-2 text-xs text-clay-400">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading comments...
            </div>
          ) : (
            <>
              {comments.map((comment) => (
                <div key={comment.id} className="group flex gap-2">
                  <div className="h-6 w-6 rounded-full bg-clay-700 flex items-center justify-center shrink-0 text-[11px] font-medium text-clay-200">
                    {comment.author.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-clay-200">{comment.author}</span>
                      <span className="text-[11px] text-clay-400">
                        {new Date(comment.created_at * 1000).toLocaleString()}
                      </span>
                      <button
                        onClick={() => handleDelete(comment.id)}
                        className="opacity-0 group-hover:opacity-100 text-clay-500 hover:text-red-400 transition-all ml-auto"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                    <MarkdownContent content={comment.body} className="mt-0.5" />
                  </div>
                </div>
              ))}

              {/* Author banner or picker */}
              <div className="space-y-2">
                {author && !changingAuthor ? (
                  <div className="flex items-center gap-2 text-[11px] text-clay-400">
                    <div className="h-4 w-4 rounded-full bg-clay-600 flex items-center justify-center text-[9px] font-medium text-clay-300 shrink-0">
                      {author.charAt(0).toUpperCase()}
                    </div>
                    <span>Commenting as <strong className="text-clay-200">{author}</strong></span>
                    <button
                      onClick={() => setChangingAuthor(true)}
                      className="text-clay-500 hover:text-clay-300 transition-colors"
                    >
                      <Pencil className="h-2.5 w-2.5" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <AuthorPicker
                      value={author}
                      onChange={(name) => {
                        setAuthor(name);
                        saveAuthor(name);
                        setChangingAuthor(false);
                      }}
                      size="sm"
                    />
                    {changingAuthor && (
                      <button
                        onClick={() => setChangingAuthor(false)}
                        className="text-[10px] text-clay-500 hover:text-clay-300"
                      >
                        cancel
                      </button>
                    )}
                  </div>
                )}

                {/* Comment input */}
                <div className="space-y-1">
                  <div className="flex gap-2">
                    <textarea
                      ref={textareaRef}
                      value={body}
                      onChange={(e) => { setBody(e.target.value); autoGrow(); }}
                      placeholder={author ? `Comment as ${author}...` : "Select a name first..."}
                      rows={1}
                      className="flex-1 bg-clay-900 border border-clay-600 rounded-md px-2.5 py-1.5 text-xs text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-clay-400 resize-none"
                      style={{ minHeight: "32px", maxHeight: "96px" }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handlePost();
                        }
                      }}
                    />
                    <Button
                      size="sm"
                      onClick={handlePost}
                      disabled={posting || !body.trim() || !author.trim()}
                      className="h-7 w-7 p-0 bg-clay-600 hover:bg-clay-500 self-end"
                    >
                      {posting ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Send className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                  <p className="text-[10px] text-clay-500 pl-0.5">
                    Enter to send · Shift+Enter for new line
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
