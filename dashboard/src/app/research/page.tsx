"use client";

import { Header } from "@/components/layout/header";
import { ResearchSearchBar } from "@/components/research/research-search-bar";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { DossierSkeleton } from "@/components/research/dossier-skeleton";
import { DossierView } from "@/components/research/dossier-view";
import { CachedResultsView } from "@/components/research/cached-results-view";
import { useResearch } from "@/hooks/use-research";

export default function ResearchPage() {
  const research = useResearch();

  return (
    <div className="flex flex-col h-full">
      <Header title="Research" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        {/* Search bar — always visible */}
        <div className="mb-6">
          <ResearchSearchBar
            onSearch={research.search}
            onClear={research.clear}
            loading={research.phase === "loading"}
            detectedEntityType={research.entityType}
          />
        </div>

        {/* Content based on phase */}
        {research.phase === "idle" && <ResearchEmptyState />}

        {research.phase === "loading" &&
          Object.keys(research.skillStates).length === 0 && (
            <DossierSkeleton />
          )}

        {research.phase === "loading" &&
          Object.keys(research.skillStates).length > 0 &&
          research.entityType && (
            <DossierView
              entityType={research.entityType}
              query={research.query}
              skillStates={research.skillStates}
              onRetry={research.retrySingle}
            />
          )}

        {research.phase === "cached" && (
          <CachedResultsView
            query={research.query}
            entries={research.cachedEntries}
            cacheAge={research.cacheAge}
            onRefresh={research.refresh}
          />
        )}

        {research.phase === "results" && research.entityType && (
          <DossierView
            entityType={research.entityType}
            query={research.query}
            skillStates={research.skillStates}
            onRetry={research.retrySingle}
          />
        )}

        {research.phase === "error" && (
          <div className="text-center py-12">
            <p className="text-sm text-red-400">
              {research.globalError || "Something went wrong"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
