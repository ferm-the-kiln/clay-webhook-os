"use client";

import { useState, useEffect, useCallback } from "react";
import { Command } from "cmdk";
import { Dialog as DialogPrimitive } from "radix-ui";
import {
  Search,
  Brain,
  Calculator,
  Filter,
  Type,
  Mail,
  Building2,
  Users,
  Globe,
  Zap,
  FileCode,
  ArrowRightLeft,
} from "lucide-react";
import { fetchTools, fetchToolCategories } from "@/lib/api";
import type { ToolDefinition, ToolCategory } from "@/lib/types";

interface ColumnCommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onSelectEnrichment: (tool: ToolDefinition) => void;
  onSelectAI: () => void;
  onSelectFormula: () => void;
  onSelectGate: () => void;
  onSelectStatic: () => void;
}

const CATEGORY_ICONS: Record<string, typeof Search> = {
  Recommended: Zap,
  Research: Globe,
  "People Search": Users,
  "Email Finding": Mail,
  "Email Verification": Mail,
  "Company Enrichment": Building2,
  "AI Processing": Brain,
  "Data Transform": FileCode,
  Outbound: ArrowRightLeft,
  "Flow Control": Filter,
};

export function ColumnCommandPalette({
  open,
  onClose,
  onSelectEnrichment,
  onSelectAI,
  onSelectFormula,
  onSelectGate,
  onSelectStatic,
}: ColumnCommandPaletteProps) {
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [categories, setCategories] = useState<ToolCategory[]>([]);

  useEffect(() => {
    if (open) {
      fetchToolCategories()
        .then((res) => setCategories(res.categories))
        .catch(() => {});
      fetchTools()
        .then((res) => setTools(res.tools))
        .catch(() => {});
    }
  }, [open]);

  // Group tools by category
  const grouped = tools.reduce<Record<string, ToolDefinition[]>>((acc, tool) => {
    const cat = tool.category || "Other";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(tool);
    return acc;
  }, {});

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 bg-black/60 z-50" />
        <DialogPrimitive.Content className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg z-50">
          <DialogPrimitive.Title className="sr-only">Add Column</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">
            Choose a column type to add to your table
          </DialogPrimitive.Description>
          <Command
            className="rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl overflow-hidden"
            label="Add Column"
          >
            <Command.Input
              placeholder="Search enrichments, formulas, filters..."
              className="w-full px-4 py-3 bg-transparent text-white text-sm border-b border-zinc-800 outline-none placeholder:text-zinc-500"
              autoFocus
            />
            <Command.List className="max-h-80 overflow-y-auto p-2">
              <Command.Empty className="py-6 text-center text-sm text-zinc-500">
                No results found.
              </Command.Empty>

              {/* Built-in column types */}
              <Command.Group heading="Column Types" className="[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-zinc-500 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
                <Command.Item
                  className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:text-white"
                  onSelect={() => {
                    onSelectAI();
                    onClose();
                  }}
                >
                  <Brain className="w-4 h-4 text-purple-400" />
                  <div>
                    <div className="font-medium">Use AI</div>
                    <div className="text-xs text-zinc-500">Describe what you want in natural language</div>
                  </div>
                </Command.Item>
                <Command.Item
                  className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:text-white"
                  onSelect={() => {
                    onSelectFormula();
                    onClose();
                  }}
                >
                  <Calculator className="w-4 h-4 text-teal-400" />
                  <div>
                    <div className="font-medium">Formula</div>
                    <div className="text-xs text-zinc-500">Computed column using other column values</div>
                  </div>
                </Command.Item>
                <Command.Item
                  className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:text-white"
                  onSelect={() => {
                    onSelectGate();
                    onClose();
                  }}
                >
                  <Filter className="w-4 h-4 text-amber-400" />
                  <div>
                    <div className="font-medium">Gate / Filter</div>
                    <div className="text-xs text-zinc-500">Filter rows by condition</div>
                  </div>
                </Command.Item>
                <Command.Item
                  className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:text-white"
                  onSelect={() => {
                    onSelectStatic();
                    onClose();
                  }}
                >
                  <Type className="w-4 h-4 text-zinc-400" />
                  <div>
                    <div className="font-medium">Static Column</div>
                    <div className="text-xs text-zinc-500">Manual text, number, or checkbox</div>
                  </div>
                </Command.Item>
              </Command.Group>

              {/* Tool catalog by category */}
              {Object.entries(grouped).map(([category, categoryTools]) => {
                const CatIcon = CATEGORY_ICONS[category] || Search;
                return (
                  <Command.Group
                    key={category}
                    heading={category}
                    className="[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-zinc-500 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:mt-2"
                  >
                    {categoryTools.map((tool) => (
                      <Command.Item
                        key={tool.id}
                        className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:text-white"
                        onSelect={() => {
                          onSelectEnrichment(tool);
                          onClose();
                        }}
                        value={`${tool.name} ${tool.description} ${category}`}
                      >
                        <CatIcon className="w-4 h-4 text-blue-400 shrink-0" />
                        <div className="min-w-0">
                          <div className="font-medium truncate">{tool.name}</div>
                          <div className="text-xs text-zinc-500 truncate">
                            {tool.description}
                          </div>
                        </div>
                        {tool.speed && (
                          <span
                            className={`ml-auto text-[10px] px-1.5 py-0.5 rounded shrink-0 ${
                              tool.speed === "fast"
                                ? "bg-emerald-500/10 text-emerald-400"
                                : tool.speed === "medium"
                                  ? "bg-amber-500/10 text-amber-400"
                                  : "bg-zinc-500/10 text-zinc-400"
                            }`}
                          >
                            {tool.speed}
                          </span>
                        )}
                      </Command.Item>
                    ))}
                  </Command.Group>
                );
              })}
            </Command.List>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
