"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function DossierSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i} className="border-clay-600 bg-clay-800/50">
          <CardHeader className="pb-3">
            <Skeleton className="h-4 w-32 bg-clay-600" />
          </CardHeader>
          <CardContent className="space-y-2.5">
            <Skeleton className="h-3 w-full bg-clay-600" />
            <Skeleton className="h-3 w-4/5 bg-clay-600" />
            <Skeleton className="h-3 w-3/5 bg-clay-600" />
            <Skeleton className="h-3 w-2/3 bg-clay-600" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
