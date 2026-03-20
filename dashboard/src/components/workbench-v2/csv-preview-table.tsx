"use client";

import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
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
      <Table className="text-xs">
        <TableHeader>
          <TableRow>
            {csvData.headers.map((h) => (
              <TableHead key={h}>
                <div>{h}</div>
                <div className="text-[10px] text-clay-300 font-normal normal-case tracking-normal">
                  {detectColumnType(
                    h,
                    csvData.rows.map((r) => r[h])
                  )}
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {csvData.rows.slice(0, 5).map((row, i) => (
            <TableRow key={i}>
              {csvData.headers.map((h) => (
                <TableCell
                  key={h}
                  className="max-w-[200px] truncate"
                >
                  {row[h]}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
