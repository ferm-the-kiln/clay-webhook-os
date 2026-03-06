"use client";

export function CsvPreview({
  headers,
  rows,
}: {
  headers: string[];
  rows: Record<string, string>[];
}) {
  const preview = rows.slice(0, 5);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
      <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
        <span className="text-xs text-zinc-500 uppercase tracking-wide">
          Preview ({rows.length} rows)
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-left text-xs text-zinc-500">
              {headers.map((h) => (
                <th key={h} className="px-3 py-2 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {preview.map((row, i) => (
              <tr key={i} className="text-zinc-300">
                {headers.map((h) => (
                  <td key={h} className="px-3 py-2 whitespace-nowrap max-w-48 truncate">
                    {row[h] || "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 5 && (
        <div className="border-t border-zinc-800 px-4 py-2 text-xs text-zinc-500">
          + {rows.length - 5} more rows
        </div>
      )}
    </div>
  );
}
