"use client";

import type { Header } from "@tanstack/react-table";
import { flexRender } from "@tanstack/react-table";
import { ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import type { DatasetSpreadsheetRow } from "./dataset-column-utils";

function renderHeaderContent(header: Header<DatasetSpreadsheetRow, unknown>) {
  if (header.isPlaceholder) return null;

  if (header.column.id === "select") {
    const val = flexRender(header.column.columnDef.header, header.getContext());
    if (val && typeof val === "object" && "checked" in (val as unknown as Record<string, unknown>)) {
      const v = val as unknown as { checked: boolean; indeterminate: boolean; onChange: (e: unknown) => void };
      return (
        <input
          type="checkbox"
          checked={v.checked}
          ref={(el) => { if (el) el.indeterminate = v.indeterminate; }}
          onChange={v.onChange}
          className="h-3.5 w-3.5 rounded border-clay-600 bg-clay-800 text-kiln-teal focus:ring-kiln-teal/50 cursor-pointer"
        />
      );
    }
    return null;
  }

  if (typeof header.column.columnDef.header === "string") {
    return header.column.columnDef.header;
  }

  return flexRender(header.column.columnDef.header, header.getContext());
}

export function DatasetHeaderCell({
  header,
}: {
  header: Header<DatasetSpreadsheetRow, unknown>;
}) {
  const canSort = header.column.getCanSort();
  const sorted = header.column.getIsSorted();
  const canResize = header.column.getCanResize();
  const source = (header.column.columnDef.meta as { group?: string })?.group;

  return (
    <th
      className="relative px-3 py-2 text-left text-xs font-medium text-clay-200 uppercase tracking-wider bg-clay-800 border-b border-clay-500 select-none whitespace-nowrap"
      style={{ width: header.getSize(), minWidth: header.getSize() }}
    >
      <div
        className={`flex items-center gap-1 ${canSort ? "cursor-pointer hover:text-clay-300" : ""}`}
        onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
      >
        {renderHeaderContent(header)}
        {source && source !== "import" && (
          <span className="text-[9px] font-normal normal-case text-clay-400 ml-0.5">
            {source}
          </span>
        )}
        {canSort && (
          <span className="ml-auto">
            {sorted === "asc" ? (
              <ArrowUp className="h-3 w-3" />
            ) : sorted === "desc" ? (
              <ArrowDown className="h-3 w-3" />
            ) : (
              <ArrowUpDown className="h-3 w-3 opacity-40" />
            )}
          </span>
        )}
      </div>
      {canResize && (
        <div
          onMouseDown={header.getResizeHandler()}
          onTouchStart={header.getResizeHandler()}
          className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-kiln-teal/50 active:bg-kiln-teal"
        />
      )}
    </th>
  );
}
