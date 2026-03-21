"use client";

import { useState, useEffect } from "react";
import { MessageCircle, Send, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchComments, postComment, deleteComment } from "@/lib/api";
import { MarkdownContent } from "./markdown-content";
import { toast } from "sonner";
import type { PortalComment } from "@/lib/types";

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

  const handlePost = async () => {
    if (!body.trim() || !author.trim()) {
      toast.error("Name and comment are required");
      return;
    }
    setPosting(true);
    try {
      const comment = await postComment(slug, updateId, { body, author });
      setComments((prev) => [...prev, comment]);
      setCount((c) => c + 1);
      setBody("");
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
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[11px] text-clay-400 hover:text-clay-200 transition-colors"
      >
        <MessageCircle className="h-3 w-3" />
        {count > 0 ? `${count} comment${count !== 1 ? "s" : ""}` : "Comment"}
      </button>

      {open && (
        <div className="mt-3 space-y-3 border-t border-clay-700 pt-3">
          {loading ? (
            <div className="flex items-center gap-2 text-xs text-clay-500">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading comments...
            </div>
          ) : (
            <>
              {comments.map((comment) => (
                <div key={comment.id} className="group flex gap-2">
                  <div className="h-6 w-6 rounded-full bg-clay-700 flex items-center justify-center shrink-0 text-[10px] font-medium text-clay-300">
                    {comment.author.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-clay-200">{comment.author}</span>
                      <span className="text-[10px] text-clay-500">
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

              {/* New comment input */}
              <div className="space-y-2">
                {!author && (
                  <input
                    type="text"
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                    placeholder="Your name"
                    className="w-full bg-clay-900 border border-clay-600 rounded-md px-2.5 py-1 text-xs text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-clay-400"
                  />
                )}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    placeholder={author ? `Comment as ${author}...` : "Add a comment..."}
                    className="flex-1 bg-clay-900 border border-clay-600 rounded-md px-2.5 py-1.5 text-xs text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-clay-400"
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
                    className="h-7 w-7 p-0 bg-clay-600 hover:bg-clay-500"
                  >
                    {posting ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Send className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
