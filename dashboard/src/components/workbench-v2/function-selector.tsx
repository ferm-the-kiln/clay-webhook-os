"use client";

import { useState, useMemo } from "react";
import type { FunctionDefinition } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Blocks,
  ChevronDown,
  Search,
  FolderOpen,
  ArrowRightLeft,
  Layers,
} from "lucide-react";

interface FunctionSelectorProps {
  functions: FunctionDefinition[];
  functionsByFolder: Record<string, FunctionDefinition[]>;
  selectedFunction: FunctionDefinition | null;
  onSelect: (func: FunctionDefinition) => void;
}

export function FunctionSelector({
  functions,
  functionsByFolder,
  selectedFunction,
  onSelect,
}: FunctionSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const filteredByFolder = useMemo(() => {
    if (!search.trim()) return functionsByFolder;

    const q = search.toLowerCase();
    const result: Record<string, FunctionDefinition[]> = {};

    for (const [folder, funcs] of Object.entries(functionsByFolder)) {
      const matches = funcs.filter(
        f =>
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
    <div>
      <label className="text-xs font-medium text-clay-300 mb-2 block">
        Function
      </label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className="w-full sm:w-auto justify-between border-clay-600 text-clay-100 bg-clay-800"
          >
            <span className="flex items-center gap-2">
              <Blocks className="h-4 w-4 text-clay-400" />
              {selectedFunction ? selectedFunction.name : "Select a function..."}
            </span>
            <ChevronDown className="h-4 w-4 text-clay-400" />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-80 p-0 bg-clay-800 border-clay-600"
          align="start"
        >
          <div className="p-2 border-b border-clay-700">
            <div className="relative">
              <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-clay-400" />
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
              <div className="px-3 py-4 text-xs text-clay-400 text-center">
                {functions.length === 0
                  ? "No functions available"
                  : "No matches found"}
              </div>
            )}
            {folderNames.map((folder) => (
              <div key={folder}>
                <div className="sticky top-0 bg-clay-800 px-3 py-1.5 flex items-center gap-1.5 border-b border-clay-700/50">
                  <FolderOpen className="h-3 w-3 text-clay-400" />
                  <span className="text-[10px] font-medium text-clay-400 uppercase tracking-wider">
                    {folder || "Uncategorized"}
                  </span>
                  <span className="text-[10px] text-clay-500">
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
                    <div className="flex items-start justify-between gap-2">
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
                          <div className="text-[11px] text-clay-400 line-clamp-1 mt-0.5">
                            {f.description}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-1 shrink-0 mt-0.5">
                        <Badge variant="secondary" className="text-[9px] px-1.5 py-0">
                          <ArrowRightLeft className="h-2.5 w-2.5 mr-0.5" />
                          {f.inputs.length}/{f.outputs.length}
                        </Badge>
                        {f.steps.length > 0 && (
                          <Badge variant="secondary" className="text-[9px] px-1.5 py-0">
                            <Layers className="h-2.5 w-2.5 mr-0.5" />
                            {f.steps.length}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
