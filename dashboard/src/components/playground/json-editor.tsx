"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

function parseJsonError(message: string): string {
  // Extract line/column info from the error message if available
  const posMatch = message.match(/position (\d+)/);
  if (posMatch) {
    return `Invalid JSON at position ${posMatch[1]}`;
  }
  const lineMatch = message.match(/line (\d+) column (\d+)/);
  if (lineMatch) {
    return `Invalid JSON at line ${lineMatch[1]}, column ${lineMatch[2]}`;
  }
  // Clean up common prefixes
  return message.replace(/^(SyntaxError: )?/, "Invalid JSON: ");
}

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
      setError(parseJsonError((e as Error).message));
    }
  }, [value]);

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-xs text-clay-200 uppercase tracking-wider font-[family-name:var(--font-sans)]">
          Data (JSON)
        </label>
        {error && (
          <span className="text-xs text-kiln-coral truncate max-w-[200px]" title={error}>
            {error}
          </span>
        )}
      </div>
      <Card
        className={`flex-1 border-clay-700 bg-clay-800 ${
          error ? "border-kiln-coral/50" : ""
        }`}
      >
        <CardContent className="p-0 h-full">
          <Textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            rows={14}
            spellCheck={false}
            className="h-full rounded-lg bg-transparent border-0 shadow-none px-4 py-3 font-[family-name:var(--font-mono)] resize-none focus-visible:border-0 focus-visible:shadow-none"
            placeholder='{ "key": "value" }'
          />
        </CardContent>
      </Card>
    </div>
  );
}
