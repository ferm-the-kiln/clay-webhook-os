import type { ColumnDef } from "@tanstack/react-table";
import type { DatasetColumn, DatasetRow } from "@/lib/types";

export interface DatasetSpreadsheetRow {
  _index: number;
  _row_id: string;
  _data: DatasetRow;
  [key: string]: unknown;
}

/**
 * Build columns from DatasetColumn metadata.
 * Groups: select, #, then data columns.
 */
export function buildDatasetColumns(
  columns: DatasetColumn[]
): ColumnDef<DatasetSpreadsheetRow, unknown>[] {
  const defs: ColumnDef<DatasetSpreadsheetRow, unknown>[] = [];

  // Select checkbox
  defs.push({
    id: "select",
    header: ({ table }) => {
      const checked = table.getIsAllRowsSelected();
      const indeterminate = table.getIsSomeRowsSelected();
      return { checked, indeterminate, onChange: table.getToggleAllRowsSelectedHandler() };
    },
    cell: ({ row }) => ({
      checked: row.getIsSelected(),
      onChange: row.getToggleSelectedHandler(),
    }),
    size: 40,
    enableSorting: false,
    enableResizing: false,
  });

  // Row number
  defs.push({
    id: "_index",
    header: "#",
    accessorFn: (row) => row._index + 1,
    size: 50,
    enableResizing: false,
  });

  // Data columns from dataset schema
  for (const col of columns) {
    if (col.name === "_row_id") continue;
    defs.push({
      id: col.name,
      header: col.name,
      accessorFn: (row) => {
        const val = row._data[col.name];
        if (val === undefined || val === null) return "";
        if (typeof val === "string") return val;
        return JSON.stringify(val);
      },
      size: 160,
      meta: { group: col.source },
    });
  }

  return defs;
}

/**
 * Build spreadsheet rows from DatasetRow array
 */
export function buildDatasetRows(rows: DatasetRow[]): DatasetSpreadsheetRow[] {
  return rows.map((row, i) => ({
    _index: i,
    _row_id: row._row_id,
    _data: row,
  }));
}
