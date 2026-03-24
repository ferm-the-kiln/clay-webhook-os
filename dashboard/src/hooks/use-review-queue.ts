"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchDestinations, pushDataToDestination } from "@/lib/api";
import type { Destination } from "@/lib/types";
import { toast } from "sonner";
import Papa from "papaparse";

export type ReviewStatus = "pending" | "approved" | "rejected" | "edited";

export interface ReviewItem {
  id: string;
  rowIndex: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  originalOutput: Record<string, unknown>;
  reviewStatus: ReviewStatus;
  editedOutput?: Record<string, unknown>;
}

export interface ReviewQueueData {
  functionId: string;
  functionName: string;
  items: ReviewItem[];
  createdAt: number;
}

const STORAGE_KEY = "kiln_review_queue";

function getApprovedItems(items: ReviewItem[]): ReviewItem[] {
  return items.filter(
    (i) => i.reviewStatus === "approved" || i.reviewStatus === "edited"
  );
}

function buildCsvRows(items: ReviewItem[]): Record<string, string>[] {
  return items.map((item) => {
    const output = item.editedOutput || item.output;
    return {
      _row: String(item.rowIndex + 1),
      ...Object.fromEntries(
        Object.entries(item.input).map(([k, v]) => [
          k,
          v == null ? "" : typeof v === "string" ? v : JSON.stringify(v),
        ])
      ),
      ...Object.fromEntries(
        Object.entries(output).map(([k, v]) => [
          `_output_${k}`,
          v == null ? "" : typeof v === "string" ? v : JSON.stringify(v),
        ])
      ),
      _review_status: item.reviewStatus,
    };
  });
}

function triggerDownload(csv: string, filename: string) {
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function useReviewQueue() {
  const [queueData, setQueueData] = useState<ReviewQueueData | null>(null);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [pushing, setPushing] = useState(false);
  const [filter, setFilter] = useState<ReviewStatus | "all">("all");

  // Load queue from sessionStorage
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        setQueueData(JSON.parse(raw));
      }
    } catch {
      // ignore
    }
  }, []);

  // Load destinations
  useEffect(() => {
    fetchDestinations()
      .then((res) => setDestinations(res.destinations))
      .catch(() => {});
  }, []);

  const items = queueData?.items || [];
  const filteredItems =
    filter === "all" ? items : items.filter((i) => i.reviewStatus === filter);

  const counts = {
    all: items.length,
    pending: items.filter((i) => i.reviewStatus === "pending").length,
    approved: items.filter(
      (i) => i.reviewStatus === "approved" || i.reviewStatus === "edited"
    ).length,
    rejected: items.filter((i) => i.reviewStatus === "rejected").length,
  };

  const updateItem = useCallback(
    (id: string, updates: Partial<ReviewItem>) => {
      setQueueData((prev) => {
        if (!prev) return prev;
        const next = {
          ...prev,
          items: prev.items.map((item) =>
            item.id === id ? { ...item, ...updates } : item
          ),
        };
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        return next;
      });
    },
    []
  );

  const approve = useCallback(
    (id: string) => updateItem(id, { reviewStatus: "approved" }),
    [updateItem]
  );

  const reject = useCallback(
    (id: string) => updateItem(id, { reviewStatus: "rejected" }),
    [updateItem]
  );

  const editOutput = useCallback(
    (id: string, editedOutput: Record<string, unknown>) =>
      updateItem(id, { reviewStatus: "edited", editedOutput }),
    [updateItem]
  );

  const approveAll = useCallback(() => {
    setQueueData((prev) => {
      if (!prev) return prev;
      const next = {
        ...prev,
        items: prev.items.map((item) =>
          item.reviewStatus === "pending"
            ? { ...item, reviewStatus: "approved" as ReviewStatus }
            : item
        ),
      };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const downloadApprovedCsv = useCallback(() => {
    if (!queueData) return;
    const approved = getApprovedItems(queueData.items);
    if (!approved.length) {
      toast.error("No approved items to download");
      return;
    }
    const csv = Papa.unparse(buildCsvRows(approved));
    triggerDownload(csv, `review-approved-${Date.now()}.csv`);
    toast.success(`Downloaded ${approved.length} rows`);
  }, [queueData]);

  const copyApprovedToClipboard = useCallback(async () => {
    if (!queueData) return;
    const approved = getApprovedItems(queueData.items);
    if (!approved.length) {
      toast.error("No approved items to copy");
      return;
    }
    const rows = buildCsvRows(approved);
    const headers = Object.keys(rows[0]);
    const tsv = [
      headers.join("\t"),
      ...rows.map((r) => headers.map((h) => r[h] ?? "").join("\t")),
    ].join("\n");
    await navigator.clipboard.writeText(tsv);
    toast.success(`Copied ${approved.length} rows to clipboard`);
  }, [queueData]);

  const pushApproved = useCallback(
    async (destinationId: string) => {
      if (!queueData) return;

      const approvedItems = getApprovedItems(queueData.items);

      if (approvedItems.length === 0) {
        toast.error("No approved items to push");
        return;
      }

      setPushing(true);
      let success = 0;
      let failed = 0;

      for (const item of approvedItems) {
        try {
          const output = item.editedOutput || item.output;
          await pushDataToDestination(destinationId, {
            ...item.input,
            ...output,
          });
          success++;
        } catch {
          failed++;
        }
      }

      setPushing(false);

      if (failed === 0) {
        toast.success(`Pushed ${success} items`);
      } else {
        toast.error(`Pushed ${success}, failed ${failed}`);
      }
    },
    [queueData]
  );

  const clearQueue = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setQueueData(null);
  }, []);

  return {
    queueData,
    items: filteredItems,
    counts,
    filter,
    setFilter,
    destinations,
    pushing,
    approve,
    reject,
    editOutput,
    approveAll,
    pushApproved,
    downloadApprovedCsv,
    copyApprovedToClipboard,
    clearQueue,
  };
}

// Called by workbench to populate the review queue
export function sendToReview(
  functionId: string,
  functionName: string,
  results: {
    rowIndex: number;
    input: Record<string, unknown>;
    output: Record<string, unknown> | null;
  }[]
) {
  const items: ReviewItem[] = results
    .filter((r) => r.output !== null)
    .map((r, i) => ({
      id: `review-${Date.now()}-${i}`,
      rowIndex: r.rowIndex,
      input: r.input,
      output: r.output!,
      originalOutput: r.output!,
      reviewStatus: "pending" as ReviewStatus,
    }));

  const data: ReviewQueueData = {
    functionId,
    functionName,
    items,
    createdAt: Date.now(),
  };

  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}
