"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { submitFeedback, deleteFeedback } from "@/lib/api";
import type { FeedbackEntry, FeedbackRating } from "@/lib/types";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export function FeedbackButtons({
  jobId,
  skill,
  model,
  clientSlug,
  existing,
  onUpdate,
}: {
  jobId: string;
  skill: string;
  model?: string;
  clientSlug?: string | null;
  existing?: FeedbackEntry[];
  onUpdate?: (entries: FeedbackEntry[]) => void;
}) {
  const [entries, setEntries] = useState<FeedbackEntry[]>(existing || []);
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const currentRating = entries.length > 0 ? entries[entries.length - 1].rating : null;

  const handleRate = async (rating: FeedbackRating) => {
    // If clicking the same rating, undo it
    if (currentRating === rating && entries.length > 0) {
      const lastEntry = entries[entries.length - 1];
      try {
        await deleteFeedback(lastEntry.id);
        const updated = entries.filter((e) => e.id !== lastEntry.id);
        setEntries(updated);
        onUpdate?.(updated);
        toast.success("Rating removed");
      } catch {
        toast.error("Failed to remove rating");
      }
      return;
    }

    // If changing rating, delete old then submit new
    if (currentRating && entries.length > 0) {
      const lastEntry = entries[entries.length - 1];
      try {
        await deleteFeedback(lastEntry.id);
      } catch {
        // continue anyway
      }
    }

    setSubmitting(true);
    try {
      const entry = await submitFeedback({
        job_id: jobId,
        skill,
        model,
        client_slug: clientSlug,
        rating,
        note: rating === "thumbs_down" && note ? note : undefined,
      });
      const updated = [...entries.filter((e) => e.job_id === jobId && e.rating !== rating), entry];
      setEntries(updated);
      onUpdate?.(updated);
      setNoteOpen(false);
      setNote("");
      toast.success(rating === "thumbs_up" ? "Rated positive" : "Rated negative");
    } catch {
      toast.error("Failed to submit rating");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={submitting}
          onClick={() => handleRate("thumbs_up")}
          className={cn(
            "h-8 px-3 border-clay-700",
            currentRating === "thumbs_up"
              ? "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/30 hover:bg-kiln-teal/20 hover:text-kiln-teal"
              : "text-clay-400 hover:text-kiln-teal hover:border-kiln-teal/30"
          )}
        >
          <ThumbsUp className="h-3.5 w-3.5 mr-1.5" />
          Good
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={submitting}
          onClick={() => {
            if (currentRating === "thumbs_down") {
              handleRate("thumbs_down");
            } else {
              setNoteOpen(true);
            }
          }}
          className={cn(
            "h-8 px-3 border-clay-700",
            currentRating === "thumbs_down"
              ? "bg-kiln-coral/15 text-kiln-coral border-kiln-coral/30 hover:bg-kiln-coral/20 hover:text-kiln-coral"
              : "text-clay-400 hover:text-kiln-coral hover:border-kiln-coral/30"
          )}
        >
          <ThumbsDown className="h-3.5 w-3.5 mr-1.5" />
          Bad
        </Button>
      </div>
      {noteOpen && (
        <div className="space-y-2">
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="What could be better? (optional)"
            className="h-16 border-clay-700 bg-clay-950 text-clay-200 placeholder:text-clay-600 text-sm resize-none"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs border-clay-700 text-clay-400"
              onClick={() => {
                setNoteOpen(false);
                setNote("");
              }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={submitting}
              className="h-7 text-xs bg-kiln-coral text-white hover:bg-kiln-coral/80"
              onClick={() => handleRate("thumbs_down")}
            >
              {submitting ? "Submitting..." : "Submit"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
