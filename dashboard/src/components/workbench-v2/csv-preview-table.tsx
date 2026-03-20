"use client";

import type { CsvData } from "@/hooks/use-function-workbench";

interface CsvPreviewTableProps {
  csvData: CsvData;
  detectColumnType: (header: string, values: string[]) => string;
}

export function CsvPreviewTable({
  csvData,
  detectColumnType,
}: CsvPreviewTableProps) {
  return (
    <div>
      <h3 className="text-sm font-medium text-clay-200 mb-2">
        Preview (first 5 rows)
      </h3>
      <div className="overflow-x-auto rounded-lg border border-clay-600">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-clay-800">
              {csvData.headers.map((h) => (
                <th
                  key={h}
                  className="px-3 py-2 text-left text-clay-300 font-medium whitespace-nowrap"
                >
                  <div>{h}</div>
                  <div className="text-[10px] text-clay-300 font-normal">
                    {detectColumnType(
                      h,
                      csvData.rows.map((r) => r[h])
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {csvData.rows.slice(0, 5).map((row, i) => (
              <tr key={i} className="border-t border-clay-700">
                {csvData.headers.map((h) => (
                  <td
                    key={h}
                    className="px-3 py-1.5 text-clay-200 whitespace-nowrap max-w-[200px] truncate"
                  >
                    {row[h]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
