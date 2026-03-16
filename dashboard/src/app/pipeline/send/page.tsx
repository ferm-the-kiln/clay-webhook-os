"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { DatasetSelector } from "@/components/pipeline/dataset-selector";
import { StageProgressBar } from "@/components/pipeline/stage-progress-bar";
import { useDatasetContext } from "@/contexts/dataset-context";
import { fetchDestinations, testDestination } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Destination } from "@/lib/types";
import { toast } from "sonner";
import { Send, ExternalLink, CheckCircle2, XCircle, Loader2 } from "lucide-react";

export default function SendPage() {
  const { datasets, activeId, setActiveId, dataset, reloadDatasets } = useDatasetContext();
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loadingDests, setLoadingDests] = useState(true);
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    fetchDestinations()
      .then((res) => setDestinations(res.destinations))
      .catch(() => {})
      .finally(() => setLoadingDests(false));
  }, []);

  const handleTest = async (dest: Destination) => {
    setTesting(dest.id);
    try {
      const res = await testDestination(dest.id);
      if (res.ok) {
        toast.success(`${dest.name}: connection successful`);
      } else {
        toast.error(`${dest.name}: ${res.error || "failed"}`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Test failed");
    } finally {
      setTesting(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Send"
        breadcrumbs={[
          { label: "Pipeline", href: "/pipeline" },
          { label: "Send" },
        ]}
      />

      <div className="flex flex-col gap-6 p-6 max-w-[1400px]">
        <DatasetSelector
          datasets={datasets}
          activeId={activeId}
          onSelect={setActiveId}
          onCreated={reloadDatasets}
        />

        {dataset && (
          <StageProgressBar completedStages={dataset.stages_completed} />
        )}

        {/* Destinations */}
        <div>
          <h2 className="text-sm font-medium text-clay-200 mb-3">Destinations</h2>
          {loadingDests ? (
            <div className="flex items-center gap-2 text-clay-300 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading destinations...
            </div>
          ) : destinations.length === 0 ? (
            <div className="border border-dashed border-clay-600 rounded-lg p-8 text-center text-clay-300">
              <Send className="h-8 w-8 mx-auto mb-3 text-clay-500" />
              <p className="text-sm font-medium mb-1">No destinations configured</p>
              <p className="text-xs">Add destinations in Settings to push enriched data.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {destinations.map((dest) => (
                <div key={dest.id} className="border border-clay-600 rounded-lg p-4 bg-clay-800/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-clay-100">{dest.name}</span>
                    <Badge variant="outline" className="text-[10px] border-clay-600 text-clay-300">
                      {dest.type === "clay_webhook" ? "Clay" : "Webhook"}
                    </Badge>
                  </div>
                  <p className="text-xs text-clay-400 truncate mb-3 font-[family-name:var(--font-mono)]">
                    {dest.url}
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTest(dest)}
                      disabled={testing === dest.id}
                      className="h-7 text-xs border-clay-600 text-clay-200"
                    >
                      {testing === dest.id ? (
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      ) : (
                        <ExternalLink className="h-3 w-3 mr-1" />
                      )}
                      Test
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled
                      className="h-7 text-xs border-clay-600 text-clay-400 cursor-not-allowed"
                    >
                      Push Dataset
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
