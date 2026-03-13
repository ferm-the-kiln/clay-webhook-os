"use client";

import type { Header } from "@tanstack/react-table";
import { flexRender } from "@tanstack/react-table";
import { ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import type { SpreadsheetRow } from "./column-utils";

function renderHeaderContent(header: Header<SpreadsheetRow, unknown>) {
  if (header.isPlaceholder) return null;

  // Select column: render a checkbox from the header function's return value
  if (header.column.id === "select") {
    const val = flexRender(header.column.columnDef.header, header.getContext());
    // The header function returns { checked, indeterminate, onChange }
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

  // All other columns: render string header
  if (typeof header.column.columnDef.header === "string") {
    return header.column.columnDef.header;
  }

  return flexRender(header.column.columnDef.header, header.getContext());
}

export function SpreadsheetHeaderCell({
  header,
}: {
  header: Header<SpreadsheetRow, unknown>;
}) {
  const canSort = header.column.getCanSort();
  const sorted = header.column.getIsSorted();
  const canResize = header.column.getCanResize();

  return (
    <th
      key={header.id}
      className="relative px-3 py-2 text-left text-xs font-medium text-clay-200 uppercase tracking-wider bg-clay-800 border-b border-clay-500 select-none whitespace-nowrap"
      style={{ width: header.getSize(), minWidth: header.getSize() }}
    >
      <div
        className={`flex items-center gap-1 ${canSort ? "cursor-pointer hover:text-clay-300" : ""}`}
        onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
      >
        {renderHeaderContent(header)}
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
      {/* Resize handle */}
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
