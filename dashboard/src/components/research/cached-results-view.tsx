"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Database, RefreshCw, Clock } from "lucide-react";
import type { MemoryEntryResponse } from "@/lib/types";

interface CachedResultsViewProps {
  query: string;
  entries: MemoryEntryResponse[];
  cacheAge: number | null;
  onRefresh: () => void;
}

function formatAge(ms: number | null): string {
  if (ms === null) return "unknown";
  const hours = ms / (1000 * 60 * 60);
  if (hours < 1) return `${Math.round(ms / (1000 * 60))}m ago`;
  if (hours < 24) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function CachedResultsView({
  query,
  entries,
  cacheAge,
  onRefresh,
}: CachedResultsViewProps) {
  return (
    <div className="mt-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-clay-100">{query}</h2>
          <div className="flex items-center gap-2 mt-1">
            <Clock className="h-3 w-3 text-clay-300" />
            <span className="text-[11px] text-clay-300">
              Last researched {formatAge(cacheAge)}
            </span>
            <Badge
              variant="outline"
              className="text-[9px] border-clay-500 text-kiln-teal"
            >
              Cached
            </Badge>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          className="h-7 text-xs border-clay-500 text-clay-200 hover:text-clay-100"
        >
          <RefreshCw className="h-3 w-3 mr-1.5" />
          Refresh
        </Button>
      </div>

      {/* Cached entries */}
      <div className="space-y-2.5">
        {entries.map((entry, i) => (
          <Card key={i} className="border-clay-600 bg-clay-800/50">
            <CardHeader className="pb-1 pt-3">
              <CardTitle className="flex items-center gap-2 text-xs font-medium text-clay-200">
                <Database className="h-3.5 w-3.5 text-kiln-teal" />
                {entry.skill}
                <span className="text-[10px] text-clay-300 font-normal">
                  {formatAge(Date.now() - entry.timestamp * 1000)}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="pb-3">
              {entry.summary && (
                <p className="text-xs text-clay-200 leading-relaxed mb-2">
                  {entry.summary}
                </p>
              )}
              {Object.keys(entry.key_fields).length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {Object.entries(entry.key_fields)
                    .slice(0, 8)
                    .map(([key, value]) => (
                      <Badge
                        key={key}
                        variant="outline"
                        className="text-[9px] border-clay-500 text-clay-300"
                      >
                        {key}: {typeof value === "string" ? value.slice(0, 30) : String(value)}
                      </Badge>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
