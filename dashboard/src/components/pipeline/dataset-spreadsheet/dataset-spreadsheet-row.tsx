"use client";

import { useState } from "react";
import type { Row } from "@tanstack/react-table";
import { motion, AnimatePresence } from "framer-motion";
import type { DatasetSpreadsheetRow } from "./dataset-column-utils";
import { DatasetCell } from "./dataset-cell";
import { DatasetRowDetail } from "./dataset-row-detail";

export function DatasetSpreadsheetRowComponent({
  row,
  style,
}: {
  row: Row<DatasetSpreadsheetRow>;
  style?: React.CSSProperties;
}) {
  const [expanded, setExpanded] = useState(false);
  const isSelected = row.getIsSelected();

  return (
    <>
      <tr
        style={style}
        onClick={() => setExpanded(!expanded)}
        className={`border-b border-clay-500 cursor-pointer transition-colors ${
          isSelected
            ? "bg-kiln-teal/5 hover:bg-kiln-teal/10"
            : "hover:bg-clay-800/50"
        } ${expanded ? "bg-clay-800/30" : ""}`}
      >
        {row.getVisibleCells().map((cell) => (
          <td
            key={cell.id}
            className="px-3 py-2"
            style={{ width: cell.column.getSize() }}
            onClick={(e) => {
              if (cell.column.id === "select") {
                e.stopPropagation();
              }
            }}
          >
            <DatasetCell columnId={cell.column.id} value={cell.getValue()} />
          </td>
        ))}
      </tr>

      <AnimatePresence>
        {expanded && (
          <tr>
            <td colSpan={row.getVisibleCells().length}>
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <DatasetRowDetail data={row.original._data} />
              </motion.div>
            </td>
          </tr>
        )}
      </AnimatePresence>
    </>
  );
}
