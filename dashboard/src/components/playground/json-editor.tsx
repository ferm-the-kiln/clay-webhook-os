"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";

export function JsonEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      JSON.parse(value);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [value]);

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-xs text-clay-500 uppercase tracking-wide font-[family-name:var(--font-sans)]">
          Data (JSON)
        </label>
        {error && (
          <span className="text-xs text-kiln-coral">Invalid JSON</span>
        )}
      </div>
      <Card
        className={`flex-1 border-clay-700 bg-clay-900 ${
          error ? "border-kiln-coral/50" : ""
        }`}
      >
        <CardContent className="p-0 h-full">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            rows={14}
            spellCheck={false}
            className="w-full h-full rounded-lg bg-transparent px-4 py-3 font-[family-name:var(--font-mono)] text-sm text-clay-100 focus:outline-none resize-none placeholder:text-clay-600"
            placeholder='{ "key": "value" }'
          />
        </CardContent>
      </Card>
    </div>
  );
}
