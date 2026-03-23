"use client";

import { useState, useMemo } from "react";
import type { FunctionDefinition } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import {
  Blocks,
  ChevronDown,
  Search,
  FolderOpen,
  MessageCircle,
  X,
} from "lucide-react";

interface FunctionPickerProps {
  functions: FunctionDefinition[];
  functionsByFolder: Record<string, FunctionDefinition[]>;
  selectedFunction: FunctionDefinition | null;
  onSelect: (func: FunctionDefinition) => void;
  onClear?: () => void;
  disabled?: boolean;
}

export function FunctionPicker({
  functions,
  functionsByFolder,
  selectedFunction,
  onSelect,
  onClear,
  disabled,
}: FunctionPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const filteredByFolder = useMemo(() => {
    if (!search.trim()) return functionsByFolder;

    const q = search.toLowerCase();
    const result: Record<string, FunctionDefinition[]> = {};

    for (const [folder, funcs] of Object.entries(functionsByFolder)) {
      const matches = funcs.filter(
        (f) =>
          f.name.toLowerCase().includes(q) ||
          f.description?.toLowerCase().includes(q)
      );
      if (matches.length > 0) {
        result[folder] = matches;
      }
    }
    return result;
  }, [functionsByFolder, search]);

  const folderNames = Object.keys(filteredByFolder).sort();

  return (
    <div className="bg-clay-800 border-b border-clay-600 px-4 py-2">
      <div className="flex items-center gap-2">
        <Popover open={open && !disabled} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button
              disabled={disabled}
              className={cn(
                "flex items-center gap-2 flex-1 text-left transition-colors",
                disabled
                  ? "cursor-default"
                  : "cursor-pointer hover:bg-clay-700/30 rounded-md -mx-1 px-1"
              )}
            >
              {selectedFunction ? (
                <Blocks className="h-4 w-4 text-clay-200 shrink-0" />
              ) : (
                <MessageCircle className="h-4 w-4 text-kiln-teal shrink-0" />
              )}
              {selectedFunction ? (
                <div className="min-w-0 flex-1">
                  <span className="text-kiln-teal font-semibold text-sm">
                    {selectedFunction.name}
                  </span>
                  {selectedFunction.description && (
                    <span className="text-[11px] text-clay-200 ml-2 truncate">
                      {selectedFunction.description}
                    </span>
                  )}
                </div>
              ) : (
                <span className="text-sm text-kiln-teal font-medium">
                  Free chat
                  <span className="text-clay-300 font-normal ml-1.5">
                    — or pick a function
                  </span>
                </span>
              )}
              {!disabled && (
                <ChevronDown className="h-4 w-4 text-clay-200 shrink-0" />
              )}
            </button>
          </PopoverTrigger>
          <PopoverContent
            className="w-80 p-0 bg-clay-800 border-clay-600"
            align="start"
          >
            <div className="p-2 border-b border-clay-700">
              <div className="relative">
                <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-clay-200" />
                <Input
                  placeholder="Search functions..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-7 h-7 text-xs bg-clay-900 border-clay-600 text-clay-100"
                />
              </div>
            </div>
            <div className="max-h-72 overflow-auto py-1">
              {folderNames.length === 0 && (
                <div className="px-3 py-4 text-xs text-clay-200 text-center">
                  {functions.length === 0
                    ? "No functions available"
                    : "No matches found"}
                </div>
              )}
              {folderNames.map((folder) => (
                <div key={folder}>
                  <div className="sticky top-0 bg-clay-800 px-3 py-1.5 flex items-center gap-1.5 border-b border-clay-700/50">
                    <FolderOpen className="h-3 w-3 text-clay-200" />
                    <span className="text-[11px] font-medium text-clay-200 uppercase tracking-wider">
                      {folder || "Uncategorized"}
                    </span>
                    <span className="text-[11px] text-clay-200">
                      ({filteredByFolder[folder].length})
                    </span>
                  </div>
                  {filteredByFolder[folder].map((f) => (
                    <button
                      key={f.id}
                      onClick={() => {
                        onSelect(f);
                        setOpen(false);
                        setSearch("");
                      }}
                      className={cn(
                        "w-full text-left px-3 py-2 hover:bg-clay-700/50 transition-colors",
                        selectedFunction?.id === f.id && "bg-kiln-teal/10"
                      )}
                    >
                      <div className="min-w-0">
                        <div
                          className={cn(
                            "text-sm font-medium truncate",
                            selectedFunction?.id === f.id
                              ? "text-kiln-teal"
                              : "text-clay-100"
                          )}
                        >
                          {f.name}
                        </div>
                        {f.description && (
                          <div className="text-[11px] text-clay-200 line-clamp-1 mt-0.5">
                            {f.description}
                          </div>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </PopoverContent>
        </Popover>

        {/* Clear button — deselect function, return to free chat */}
        {selectedFunction && onClear && (
          <button
            onClick={onClear}
            className="text-clay-400 hover:text-clay-100 transition-colors shrink-0 p-1 rounded hover:bg-clay-700"
            title="Clear function — return to free chat"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
