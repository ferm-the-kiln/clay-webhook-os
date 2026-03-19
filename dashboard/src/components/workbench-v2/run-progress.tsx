"use client";

import { Loader2 } from "lucide-react";

interface RunProgressProps {
  done: number;
  total: number;
}

export function RunProgress({ done, total }: RunProgressProps) {
  const pct = total > 0 ? (done / total) * 100 : 0;

  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <Loader2 className="h-10 w-10 text-kiln-teal animate-spin" />
      <div className="text-lg font-semibold text-clay-100">Processing...</div>
      <div className="text-sm text-clay-300">
        {done}/{total} rows processed
      </div>
      <div className="w-64 h-2 bg-clay-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-kiln-teal rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
