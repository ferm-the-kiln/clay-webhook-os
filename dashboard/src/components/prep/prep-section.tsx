"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface PrepSectionProps {
  title: string;
  icon: LucideIcon;
  iconColor?: string;
  loading: boolean;
  error?: string | null;
  onRetry?: () => void;
  children: React.ReactNode;
}

export function PrepSection({
  title,
  icon: Icon,
  iconColor = "text-kiln-teal",
  loading,
  error,
  onRetry,
  children,
}: PrepSectionProps) {
  return (
    <Card className="border-clay-600 bg-clay-800/50">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-clay-200">
          <Icon className={cn("h-4 w-4", iconColor)} />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading && (
          <div className="space-y-2.5">
            <Skeleton className="h-3 w-full bg-clay-600" />
            <Skeleton className="h-3 w-4/5 bg-clay-600" />
            <Skeleton className="h-3 w-3/5 bg-clay-600" />
          </div>
        )}

        {error && !loading && (
          <div className="flex items-center gap-2 text-xs text-red-400">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">{error}</span>
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

        {!loading && !error && children}
      </CardContent>
    </Card>
  );
}
