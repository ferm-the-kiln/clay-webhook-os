"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function CsvPreview({
  headers,
  rows,
}: {
  headers: string[];
  rows: Record<string, string>[];
}) {
  const preview = rows.slice(0, 5);

  return (
    <div className="rounded-xl border border-clay-800 bg-clay-900 overflow-hidden">
      <div className="flex items-center justify-between border-b border-clay-800 px-4 py-2">
        <span className="text-xs text-clay-500 uppercase tracking-wide font-[family-name:var(--font-sans)]">
          Preview ({rows.length} rows)
        </span>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-clay-800 hover:bg-transparent">
              {headers.map((h) => (
                <TableHead
                  key={h}
                  className="text-clay-500 text-xs whitespace-nowrap"
                >
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {preview.map((row, i) => (
              <TableRow
                key={i}
                className="border-clay-800 hover:bg-clay-800/50"
              >
                {headers.map((h) => (
                  <TableCell
                    key={h}
                    className="text-clay-300 whitespace-nowrap max-w-48 truncate"
                  >
                    {row[h] || "\u2014"}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {rows.length > 5 && (
        <div className="border-t border-clay-800 px-4 py-2 text-xs text-clay-500">
          + {rows.length - 5} more rows
        </div>
      )}
    </div>
  );
}
