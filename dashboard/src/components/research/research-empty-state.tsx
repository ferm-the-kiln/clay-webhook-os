"use client";

import { Search } from "lucide-react";

export function ResearchEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-clay-700/50 border border-clay-600 mb-4">
        <Search className="h-6 w-6 text-clay-300" />
      </div>
      <h3 className="text-sm font-medium text-clay-200 mb-1">
        Research any entity
      </h3>
      <p className="text-xs text-clay-300 max-w-xs">
        Search for a company or person to get a structured dossier with tech
        stack, key people, ICP fit, and recommended angles.
      </p>
    </div>
  );
}
