"use client";

import { useState } from "react";
import type { Destination, Job } from "@/lib/types";
import { pushToDestination } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Send, ChevronDown, ChevronUp } from "lucide-react";
import { toast } from "sonner";

interface PushDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  destinations: Destination[];
  jobs: Job[];
}

export function PushDialog({ open, onOpenChange, destinations, jobs }: PushDialogProps) {
  const [selectedId, setSelectedId] = useState("");
  const [pushing, setPushing] = useState(false);
  const [errorsExpanded, setErrorsExpanded] = useState(false);
  const [lastErrors, setLastErrors] = useState<{ job_id: string; error: string }[]>([]);

  const completedJobs = jobs.filter((j) => j.status === "completed");
  const selectedDest = destinations.find((d) => d.id === selectedId);

  const handlePush = async () => {
    if (!selectedId || completedJobs.length === 0) return;
    setPushing(true);
    setLastErrors([]);

    try {
      const result = await pushToDestination(
        selectedId,
        completedJobs.map((j) => j.id)
      );

      if (result.failed === 0) {
        toast.success("Push complete", {
          description: `${result.success} rows sent to ${result.destination_name}`,
        });
        onOpenChange(false);
      } else {
        toast.warning("Push completed with errors", {
          description: `${result.success} succeeded, ${result.failed} failed`,
        });
        setLastErrors(result.errors);
      }
    } catch (e) {
      toast.error("Push failed", { description: (e as Error).message });
    } finally {
      setPushing(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-clay-800 bg-clay-950">
        <DialogHeader>
          <DialogTitle className="text-clay-100">Push to Destination</DialogTitle>
          <DialogDescription className="text-clay-500">
            Send {completedJobs.length} completed rows to an external destination.
          </DialogDescription>
        </DialogHeader>

        {destinations.length === 0 ? (
          <p className="text-sm text-clay-500">
            No destinations configured. Go to Settings to add one.
          </p>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
                Destination
              </label>
              <Select value={selectedId} onValueChange={setSelectedId}>
                <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue placeholder="Select destination..." />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  {destinations.map((d) => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.name} ({d.type === "clay_webhook" ? "Clay" : "Webhook"})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedDest && (
              <div className="rounded-lg border border-clay-800 bg-clay-900/50 p-3 text-sm space-y-1">
                <p className="text-clay-300">
                  Push <span className="text-kiln-teal font-medium">{completedJobs.length}</span> rows
                  to <span className="text-clay-100 font-medium">{selectedDest.name}</span>
                </p>
                <p className="text-clay-500 text-xs font-[family-name:var(--font-mono)] truncate">
                  {selectedDest.url}
                </p>
              </div>
            )}

            <Button
              onClick={handlePush}
              disabled={!selectedId || completedJobs.length === 0 || pushing}
              className="w-full bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
            >
              <Send className="h-4 w-4 mr-2" />
              {pushing ? "Pushing..." : `Push ${completedJobs.length} rows`}
            </Button>

            {lastErrors.length > 0 && (
              <div className="rounded-lg border border-kiln-coral/30 bg-kiln-coral/5 overflow-hidden">
                <button
                  onClick={() => setErrorsExpanded((e) => !e)}
                  className="w-full flex items-center justify-between p-3 text-left text-sm text-kiln-coral"
                >
                  <span>{lastErrors.length} errors</span>
                  {errorsExpanded ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>
                {errorsExpanded && (
                  <div className="px-3 pb-3 space-y-1 max-h-40 overflow-y-auto">
                    {lastErrors.map((err, i) => (
                      <p key={i} className="text-xs text-clay-400">
                        <span className="text-clay-500 font-[family-name:var(--font-mono)]">
                          {err.job_id}:
                        </span>{" "}
                        {err.error}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
