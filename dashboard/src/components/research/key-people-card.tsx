"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Users, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { WebhookResponse } from "@/lib/types";
import type { SkillStatus } from "@/hooks/use-research";

interface KeyPeopleCardProps {
  data: WebhookResponse | null;
  status: SkillStatus;
  error?: string | null;
  onRetry?: () => void;
}

interface PersonEntry {
  name?: string;
  title?: string;
  level?: string;
  function?: string;
  relevance?: string;
  linkedin_url?: string;
}

export function KeyPeopleCard({
  data,
  status,
  error,
  onRetry,
}: KeyPeopleCardProps) {
  const people: PersonEntry[] =
    data && Array.isArray(data.stakeholders)
      ? (data.stakeholders as PersonEntry[])
      : data && Array.isArray(data.key_people)
        ? (data.key_people as PersonEntry[])
        : [];

  return (
    <Card className="border-clay-600 bg-clay-800/50">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-clay-200">
          <Users className="h-4 w-4 text-purple-400" />
          Key People
        </CardTitle>
      </CardHeader>
      <CardContent>
        {status === "loading" && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 rounded-full bg-clay-600" />
                <div className="flex-1 space-y-1">
                  <Skeleton className="h-3 w-28 bg-clay-600" />
                  <Skeleton className="h-2.5 w-40 bg-clay-600" />
                </div>
              </div>
            ))}
          </div>
        )}

        {status === "error" && (
          <div className="flex items-center gap-2 text-xs text-red-400">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">{error || "Failed to load"}</span>
            {onRetry && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRetry}
                className="h-6 px-2 text-[10px] text-clay-300 hover:text-clay-100"
              >
                <RefreshCw className="h-3 w-3 mr-1" /> Retry
              </Button>
            )}
          </div>
        )}

        {status === "done" && (
          <>
            {people.length > 0 ? (
              <div className="space-y-2.5">
                {people.slice(0, 5).map((person, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 py-1.5 border-b border-clay-700 last:border-0"
                  >
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-clay-700 text-clay-200 text-xs font-medium shrink-0">
                      {person.name
                        ? person.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")
                            .slice(0, 2)
                        : "?"}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-clay-100 truncate">
                        {person.name || "Unknown"}
                      </p>
                      {person.title && (
                        <p className="text-[11px] text-clay-300 truncate">
                          {person.title}
                        </p>
                      )}
                      <div className="flex gap-1 mt-1">
                        {person.level && (
                          <Badge
                            variant="outline"
                            className="text-[9px] border-clay-500 text-clay-300"
                          >
                            {person.level}
                          </Badge>
                        )}
                        {person.function && (
                          <Badge
                            variant="outline"
                            className="text-[9px] border-clay-500 text-clay-300"
                          >
                            {person.function}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-clay-300">
                {data?.person_summary
                  ? String(data.person_summary)
                  : "No key people found"}
              </p>
            )}
          </>
        )}

        {status === "idle" && (
          <p className="text-xs text-clay-300">Waiting...</p>
        )}
      </CardContent>
    </Card>
  );
}
