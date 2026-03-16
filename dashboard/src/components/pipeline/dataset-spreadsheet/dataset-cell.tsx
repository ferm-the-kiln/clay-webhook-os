"use client";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function DatasetCell({
  columnId,
  value,
}: {
  columnId: string;
  value: unknown;
}) {
  // Checkbox column
  if (columnId === "select") {
    if (!value || typeof value !== "object") return null;
    const v = value as { checked: boolean; onChange: (e: unknown) => void };
    return (
      <input
        type="checkbox"
        checked={v.checked}
        onChange={v.onChange}
        className="h-3.5 w-3.5 rounded border-clay-600 bg-clay-800 text-kiln-teal focus:ring-kiln-teal/50 cursor-pointer"
      />
    );
  }

  // Index column
  if (columnId === "_index") {
    return (
      <span className="text-clay-200 font-[family-name:var(--font-mono)] text-xs">
        {String(value)}
      </span>
    );
  }

  // Generic cell with tooltip for truncated content
  const strValue = value === null || value === undefined ? "" : String(value);
  if (!strValue) {
    return <span className="text-clay-300">{"\u2014"}</span>;
  }

  const isTruncated = strValue.length > 60;

  if (isTruncated) {
    return (
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="text-xs text-clay-300 block truncate max-w-full cursor-default">
              {strValue}
            </span>
          </TooltipTrigger>
          <TooltipContent
            side="bottom"
            className="max-w-sm bg-clay-800 border-clay-700 text-clay-200 text-xs"
          >
            <pre className="whitespace-pre-wrap font-[family-name:var(--font-mono)]">
              {strValue}
            </pre>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <span className="text-xs text-clay-300 block truncate">{strValue}</span>
  );
}
