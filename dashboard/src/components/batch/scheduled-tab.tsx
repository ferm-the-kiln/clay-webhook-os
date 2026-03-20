"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Ban, RefreshCw } from "lucide-react";
import { fetchScheduledBatches, cancelScheduledBatch } from "@/lib/api";
import type { ScheduledBatch } from "@/lib/types";

export function ScheduledTab() {
  const [batches, setBatches] = useState<ScheduledBatch[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const resp = await fetchScheduledBatches();
      setBatches(resp.batches);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  const handleCancel = async (batchId: string) => {
    await cancelScheduledBatch(batchId);
    load();
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "scheduled":
        return "bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30";
      case "enqueued":
        return "bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30";
      case "cancelled":
        return "bg-clay-500/10 text-clay-200 border-clay-500/30";
      default:
        return "bg-clay-500/10 text-clay-200 border-clay-500/30";
    }
  };

  if (loading) {
    return (
      <div className="text-center py-8 text-sm text-clay-200">
        Loading scheduled batches...
      </div>
    );
  }

  if (batches.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-clay-200">
        No scheduled batches
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-clay-200 font-[family-name:var(--font-sans)]">
          Scheduled Batches
        </h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={load}
          className="h-7 text-clay-200 hover:text-clay-300"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Refresh
        </Button>
      </div>
      {batches.map((batch) => (
        <Card key={batch.id} className="border-clay-500">
          <CardContent className="p-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-[family-name:var(--font-mono)] text-clay-200">
                    {batch.id}
                  </span>
                  <Badge
                    variant="outline"
                    className={`text-[10px] ${statusColor(batch.status)}`}
                  >
                    {batch.status}
                  </Badge>
                </div>
                <div className="flex gap-3 mt-1 text-[11px] text-clay-200">
                  <span>Skill: {batch.skill}</span>
                  <span>Rows: {batch.total_rows}</span>
                  <span>
                    Scheduled:{" "}
                    {new Date(batch.scheduled_at * 1000).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
            {batch.status === "scheduled" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleCancel(batch.id)}
                className="h-7 bg-kiln-coral/10 text-kiln-coral border-kiln-coral/30 hover:bg-kiln-coral/20"
              >
                <Ban className="h-3 w-3 mr-1" />
                Cancel
              </Button>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
