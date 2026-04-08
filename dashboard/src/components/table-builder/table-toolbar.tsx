"use client";

import { useState, useRef } from "react";
import {
  Upload,
  Plus,
  Download,
  Trash2,
  Play,
  Square,
  RefreshCw,
  Settings,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { TableDefinition } from "@/lib/types";

interface TableToolbarProps {
  table: TableDefinition;
  totalRows: number;
  executing: boolean;
  onRename: (name: string) => Promise<void>;
  onImportCsv: (file: File) => Promise<void>;
  onAddRow: () => void;
  onRefresh: () => Promise<void>;
  selectedCount: number;
  onDeleteSelected: () => void;
  onExecute?: (options?: { limit?: number }) => void;
  onStop?: () => void;
  onSettings?: () => void;
  onSaveAsFunction?: () => void;
}

export function TableToolbar({
  table,
  totalRows,
  executing,
  onRename,
  onImportCsv,
  onAddRow,
  onRefresh,
  selectedCount,
  onDeleteSelected,
  onExecute,
  onStop,
  onSettings,
  onSaveAsFunction,
}: TableToolbarProps) {
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState(table.name);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleNameBlur = async () => {
    setEditingName(false);
    if (nameValue.trim() && nameValue !== table.name) {
      await onRename(nameValue.trim());
    } else {
      setNameValue(table.name);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) await onImportCsv(file);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-clay-700 bg-clay-950/80 backdrop-blur-sm shrink-0">
      {/* Table name */}
      {editingName ? (
        <Input
          value={nameValue}
          onChange={(e) => setNameValue(e.target.value)}
          onBlur={handleNameBlur}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleNameBlur();
            if (e.key === "Escape") {
              setNameValue(table.name);
              setEditingName(false);
            }
          }}
          autoFocus
          className="w-64 h-8 bg-clay-900 border-clay-500 text-white text-sm"
        />
      ) : (
        <button
          onClick={() => setEditingName(true)}
          className="text-sm font-medium text-white hover:text-kiln-teal transition-colors truncate max-w-64"
        >
          {table.name}
        </button>
      )}

      {/* Row count badge */}
      <span className="text-xs text-clay-300 bg-clay-700 px-2 py-0.5 rounded">
        {totalRows} rows
      </span>

      {/* Save as Function */}
      {onSaveAsFunction && (
        <Button
          variant="ghost"
          size="sm"
          className="text-clay-200 hover:text-white h-7 text-xs"
          onClick={onSaveAsFunction}
          title="Save table as reusable function"
        >
          <Layers className="w-3 h-3 mr-1" />
          Save as Function
        </Button>
      )}

      {/* Settings gear */}
      {onSettings && (
        <Button
          variant="ghost"
          size="icon"
          className="text-clay-200 hover:text-white h-7 w-7"
          onClick={onSettings}
          title="Function settings"
        >
          <Settings className="w-3.5 h-3.5" />
        </Button>
      )}

      <div className="flex-1" />

      {/* Selection actions */}
      {selectedCount > 0 && (
        <Button
          variant="ghost"
          size="sm"
          className="text-red-400 hover:text-red-300 h-7 text-xs"
          onClick={onDeleteSelected}
        >
          <Trash2 className="w-3 h-3 mr-1" />
          Delete {selectedCount}
        </Button>
      )}

      {/* Import CSV */}
      <input
        ref={fileRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFileChange}
      />
      <Button
        variant="ghost"
        size="sm"
        className="text-clay-200 hover:text-white h-7 text-xs"
        onClick={() => fileRef.current?.click()}
      >
        <Upload className="w-3 h-3 mr-1" />
        Import
      </Button>

      {/* Add Row */}
      <Button
        variant="ghost"
        size="sm"
        className="text-clay-200 hover:text-white h-7 text-xs"
        onClick={onAddRow}
      >
        <Plus className="w-3 h-3 mr-1" />
        Row
      </Button>

      {/* Refresh */}
      <Button
        variant="ghost"
        size="icon"
        className="text-clay-200 hover:text-white h-7 w-7"
        onClick={onRefresh}
      >
        <RefreshCw className="w-3 h-3" />
      </Button>

      {/* Run controls */}
      {executing ? (
        <Button
          size="sm"
          className="bg-red-600 hover:bg-red-500 text-white h-7 text-xs"
          onClick={onStop}
        >
          <Square className="w-3 h-3 mr-1" />
          Stop
        </Button>
      ) : (
        <div className="flex items-center">
          <Button
            size="sm"
            className="bg-emerald-600 hover:bg-emerald-500 text-white h-7 text-xs rounded-r-none"
            disabled={totalRows === 0}
            onClick={() => onExecute?.({ limit: 10 })}
          >
            <Play className="w-3 h-3 mr-1" />
            Save & Run 10
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="sm"
                className="bg-emerald-700 hover:bg-emerald-600 text-white h-7 text-xs rounded-l-none border-l border-emerald-500/30 px-1.5"
                disabled={totalRows === 0}
              >
                <svg className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
                  <path d="M3 5l3 3 3-3H3z" />
                </svg>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-clay-900 border-clay-500">
              <DropdownMenuItem
                className="text-clay-100"
                onClick={() => onExecute?.({ limit: 10 })}
              >
                Run first 10 rows
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-clay-100"
                onClick={() => onExecute?.()}
              >
                Run all rows
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </div>
  );
}
