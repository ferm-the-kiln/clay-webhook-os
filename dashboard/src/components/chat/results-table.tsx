"use client";

import { useMemo } from "react";
import { Download, XCircle, Loader2 } from "lucide-react";
import type { RowStatus } from "@/hooks/use-chat";
import type { FunctionOutput } from "@/lib/types";

interface ResultsTableProps {
  rowStatuses: RowStatus[];
  columns: FunctionOutput[];
  onExportCsv: () => void;
  streaming: boolean;
}

export function ResultsTable({
  rowStatuses,
  columns,
  onExportCsv,
  streaming,
}: ResultsTableProps) {
  const doneCount = rowStatuses.filter((r) => r.status === "done").length;

  // Derive columns from first done row when no explicit columns defined
  const resolvedColumns = useMemo<FunctionOutput[]>(() => {
    if (columns.length > 0) return columns;
    const firstDone = rowStatuses.find((r) => r.status === "done");
    if (!firstDone?.result) return [];
    return Object.keys(firstDone.result).map((key) => ({
      key,
      type: "string",
      description: "",
    }));
  }, [columns, rowStatuses]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-clay-700">
        <div className="flex items-center">
          <span className="text-xs font-semibold text-clay-300">Results</span>
          <span className="ml-2 text-xs text-clay-300 font-mono">
            ({doneCount}/{rowStatuses.length})
          </span>
        </div>
        <button
          onClick={onExportCsv}
          disabled={doneCount === 0}
          className="flex items-center gap-1.5 text-xs text-clay-300 hover:text-clay-100 px-2 py-1 rounded hover:bg-clay-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Download className="h-3 w-3" />
          Export CSV
        </button>
      </div>

      {/* Table container */}
      <div className="flex-1 overflow-auto">
        {resolvedColumns.length > 0 ? (
          <table className="w-full text-xs">
            <thead>
              <tr className="sticky top-0 bg-clay-900 z-10">
                {resolvedColumns.map((col) => (
                  <th
                    key={col.key}
                    className="text-left px-3 py-2 text-clay-300 font-semibold font-mono border-b border-clay-700 whitespace-nowrap"
                  >
                    {col.key}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rowStatuses.map((row) => {
                if (row.status === "done" && row.result) {
                  return (
                    <tr
                      key={row.index}
                      className="border-b border-clay-800 hover:bg-clay-900/50"
                    >
                      {resolvedColumns.map((col) => {
                        const value = row.result?.[col.key];
                        let display: string;
                        if (value === null || value === undefined) {
                          display = "--";
                        } else if (
                          typeof value === "object"
                        ) {
                          display = JSON.stringify(value);
                        } else {
                          display = String(value);
                        }
                        return (
                          <td
                            key={col.key}
                            className={`px-3 py-2 font-mono max-w-[200px] truncate ${
                              value === null || value === undefined
                                ? "text-clay-300"
                                : "text-clay-100"
                            }`}
                            title={display !== "--" ? display : undefined}
                          >
                            {display}
                          </td>
                        );
                      })}
                    </tr>
                  );
                }

                if (row.status === "error") {
                  const errorMsg = row.error || "Failed";
                  const truncatedError =
                    errorMsg.length > 60
                      ? `${errorMsg.slice(0, 60)}...`
                      : errorMsg;
                  return (
                    <tr
                      key={row.index}
                      className="border-b border-clay-800 bg-kiln-coral/5"
                    >
                      <td
                        colSpan={resolvedColumns.length}
                        className="px-3 py-2 text-kiln-coral"
                      >
                        <div className="flex items-center gap-1.5">
                          <XCircle className="h-3 w-3 flex-shrink-0" />
                          <span>
                            Row {row.index + 1}: {truncatedError}
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                }

                if (row.status === "running") {
                  return (
                    <tr key={row.index} className="border-b border-clay-800">
                      <td
                        colSpan={resolvedColumns.length}
                        className="px-3 py-2 text-clay-300"
                      >
                        <div className="flex items-center gap-1.5">
                          <Loader2 className="h-3 w-3 animate-spin text-kiln-teal flex-shrink-0" />
                          <span>Processing row {row.index + 1}...</span>
                        </div>
                      </td>
                    </tr>
                  );
                }

                // pending
                return (
                  <tr
                    key={row.index}
                    className="border-b border-clay-800 opacity-40"
                  >
                    <td
                      colSpan={resolvedColumns.length}
                      className="px-3 py-2 text-clay-300"
                    >
                      Row {row.index + 1}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          // No columns yet -- show a waiting state
          !streaming ? null : (
            <div className="flex items-center justify-center py-8 text-xs text-clay-300">
              <Loader2 className="h-4 w-4 animate-spin text-kiln-teal mr-2" />
              Waiting for first result...
            </div>
          )
        )}
      </div>
    </div>
  );
}
