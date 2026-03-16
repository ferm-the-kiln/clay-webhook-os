"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Database } from "lucide-react";
import type { DatasetSummary } from "@/lib/types";
import { DatasetImportDialog } from "./dataset-import-dialog";

interface DatasetSelectorProps {
  datasets: DatasetSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreated: () => void;
}

export function DatasetSelector({
  datasets,
  activeId,
  onSelect,
  onCreated,
}: DatasetSelectorProps) {
  const [showImport, setShowImport] = useState(false);

  return (
    <div className="flex items-center gap-3">
      <Database className="h-4 w-4 text-clay-300" />
      <Select value={activeId ?? ""} onValueChange={onSelect}>
        <SelectTrigger className="w-[240px] bg-clay-700 border-clay-600 text-clay-100">
          <SelectValue placeholder="Select a dataset..." />
        </SelectTrigger>
        <SelectContent className="bg-clay-700 border-clay-600">
          {datasets.map((ds) => (
            <SelectItem key={ds.id} value={ds.id} className="text-clay-100">
              <span className="flex items-center gap-2">
                {ds.name}
                <span className="text-xs text-clay-300">
                  {ds.row_count} rows · {ds.column_count} cols
                </span>
              </span>
            </SelectItem>
          ))}
          {datasets.length === 0 && (
            <div className="px-3 py-2 text-sm text-clay-300">
              No datasets yet
            </div>
          )}
        </SelectContent>
      </Select>

      <Button
        variant="outline"
        size="sm"
        className="border-clay-600 text-clay-200 hover:bg-clay-700"
        onClick={() => setShowImport(true)}
      >
        <Plus className="h-3.5 w-3.5 mr-1.5" />
        New Dataset
      </Button>

      <DatasetImportDialog
        open={showImport}
        onOpenChange={setShowImport}
        onCreated={(id) => {
          onSelect(id);
          onCreated();
          setShowImport(false);
        }}
      />
    </div>
  );
}
