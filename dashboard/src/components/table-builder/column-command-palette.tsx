"use client";

import { useState, useEffect } from "react";
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
  Sparkles,
  Clock,
  Layers,
  Unplug,
  Shuffle,
  Link2,
  Terminal,
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
  onAIBuilder?: () => void;
  onSelectHttp?: () => void;
  onSelectWaterfall?: () => void;
  onSelectLookup?: () => void;
  onSelectScript?: () => void;
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

const CATEGORY_ORDER = [
  "Recommended",
  "Research",
  "People Search",
  "Email Finding",
  "Email Verification",
  "Company Enrichment",
  "AI Processing",
  "Data Transform",
  "Outbound",
  "Flow Control",
];

/** Persist recent tool selections in localStorage */
function getRecentTools(): string[] {
  try {
    return JSON.parse(localStorage.getItem("recentTools") || "[]");
  } catch {
    return [];
  }
}

function addRecentTool(toolId: string) {
  const recent = getRecentTools().filter((id) => id !== toolId);
  recent.unshift(toolId);
  localStorage.setItem("recentTools", JSON.stringify(recent.slice(0, 5)));
}

const ITEM_CLASS =
  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:text-white transition-colors";

const GROUP_HEADING_CLASS =
  "[&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-2";

/** Multi-step presets that add multiple columns at once */
const MULTI_STEP_PRESETS = [
  {
    id: "email-waterfall",
    name: "Email Waterfall",
    description: "Findymail → verify email",
    icon: Mail,
    color: "text-emerald-400",
    toolId: "findymail",
  },
  {
    id: "company-research",
    name: "Company Research",
    description: "Web search → AI summary",
    icon: Globe,
    color: "text-blue-400",
    toolId: "web_search",
  },
  {
    id: "contact-finder",
    name: "Contact Finder",
    description: "Find people at company (Apollo)",
    icon: Users,
    color: "text-amber-400",
    toolId: "apollo_people",
  },
  {
    id: "company-enrichment",
    name: "Company Enrichment",
    description: "Company data via Apollo",
    icon: Building2,
    color: "text-purple-400",
    toolId: "apollo_org",
  },
];

export function ColumnCommandPalette({
  open,
  onClose,
  onSelectEnrichment,
  onSelectAI,
  onSelectFormula,
  onSelectGate,
  onSelectStatic,
  onAIBuilder,
  onSelectHttp,
  onSelectWaterfall,
  onSelectLookup,
  onSelectScript,
}: ColumnCommandPaletteProps) {
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [categories, setCategories] = useState<ToolCategory[]>([]);
  const [recentIds, setRecentIds] = useState<string[]>([]);

  useEffect(() => {
    if (open) {
      fetchToolCategories()
        .then((res) => setCategories(res.categories))
        .catch(() => {});
      fetchTools()
        .then((res) => setTools(res.tools))
        .catch(() => {});
      setRecentIds(getRecentTools());
    }
  }, [open]);

  // Group tools by category, sorted
  const grouped = tools.reduce<Record<string, ToolDefinition[]>>((acc, tool) => {
    const cat = tool.category || "Other";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(tool);
    return acc;
  }, {});

  const sortedCategories = CATEGORY_ORDER.filter((c) => grouped[c]);
  const otherCategories = Object.keys(grouped).filter(
    (c) => !CATEGORY_ORDER.includes(c),
  );

  // Recent tools
  const recentTools = recentIds
    .map((id) => tools.find((t) => t.id === id))
    .filter(Boolean) as ToolDefinition[];

  const handleSelectTool = (tool: ToolDefinition) => {
    addRecentTool(tool.id);
    onSelectEnrichment(tool);
    onClose();
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 bg-black/60 z-50" />
        <DialogPrimitive.Content className="fixed top-[10%] left-1/2 -translate-x-1/2 w-full max-w-3xl z-50">
          <DialogPrimitive.Title className="sr-only">Add Column</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">
            Choose a column type to add to your table
          </DialogPrimitive.Description>
          <Command
            className="rounded-xl border border-zinc-700 bg-zinc-900 shadow-2xl overflow-hidden"
            label="Add Column"
          >
            {/* Search bar */}
            <div className="border-b border-zinc-800 px-4 py-3 flex items-center gap-3">
              <Search className="w-4 h-4 text-zinc-500 shrink-0" />
              <Command.Input
                placeholder="Search enrichments, AI, formulas, filters..."
                className="flex-1 bg-transparent text-white text-sm outline-none placeholder:text-zinc-500"
                autoFocus
              />
            </div>

            <Command.List className="max-h-[60vh] overflow-y-auto p-3">
              <Command.Empty className="py-10 text-center text-sm text-zinc-500">
                No results found.
              </Command.Empty>

              {/* AI Builder — top hero card */}
              {onAIBuilder && (
                <Command.Group className="mb-3">
                  <Command.Item
                    className="flex items-center gap-4 px-4 py-3 rounded-lg bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20 text-white cursor-pointer data-[selected=true]:border-purple-500/40 data-[selected=true]:bg-purple-500/15 transition-all"
                    onSelect={() => {
                      onAIBuilder();
                      onClose();
                    }}
                    value="ai builder describe goal create columns automatically"
                  >
                    <div className="w-9 h-9 rounded-lg bg-purple-500/20 flex items-center justify-center shrink-0">
                      <Sparkles className="w-5 h-5 text-purple-400" />
                    </div>
                    <div>
                      <div className="font-semibold text-sm">AI Builder</div>
                      <div className="text-xs text-zinc-400">
                        Describe what you want to achieve and AI will build the columns for you
                      </div>
                    </div>
                  </Command.Item>
                </Command.Group>
              )}

              {/* Recent tools */}
              {recentTools.length > 0 && (
                <Command.Group
                  heading="Recent"
                  className={`${GROUP_HEADING_CLASS} [&_[cmdk-group-heading]]:text-zinc-500`}
                >
                  {recentTools.map((tool) => {
                    const CatIcon =
                      CATEGORY_ICONS[tool.category || ""] || Search;
                    return (
                      <Command.Item
                        key={`recent-${tool.id}`}
                        className={ITEM_CLASS}
                        onSelect={() => handleSelectTool(tool)}
                        value={`recent ${tool.name} ${tool.description}`}
                      >
                        <Clock className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                        <CatIcon className="w-4 h-4 text-blue-400 shrink-0" />
                        <div className="min-w-0 flex-1">
                          <div className="font-medium">{tool.name}</div>
                        </div>
                        <SpeedBadge speed={tool.speed} />
                      </Command.Item>
                    );
                  })}
                </Command.Group>
              )}

              {/* Quick templates */}
              <Command.Group
                heading="Quick Start"
                className={`${GROUP_HEADING_CLASS} [&_[cmdk-group-heading]]:text-kiln-teal`}
              >
                <div className="grid grid-cols-2 gap-2 px-1 pb-2">
                  {MULTI_STEP_PRESETS.map((preset) => {
                    const Icon = preset.icon;
                    return (
                      <Command.Item
                        key={preset.id}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-zinc-800 text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:border-zinc-600 data-[selected=true]:text-white transition-all"
                        onSelect={() => {
                          const tool = tools.find(
                            (t) => t.id === preset.toolId,
                          );
                          if (tool) {
                            handleSelectTool(tool);
                          }
                        }}
                        value={`${preset.name} ${preset.description}`}
                      >
                        <Icon className={`w-4 h-4 ${preset.color} shrink-0`} />
                        <div className="min-w-0">
                          <div className="font-medium text-xs">
                            {preset.name}
                          </div>
                          <div className="text-[11px] text-zinc-500 truncate">
                            {preset.description}
                          </div>
                        </div>
                      </Command.Item>
                    );
                  })}
                </div>
              </Command.Group>

              {/* Built-in column types */}
              <Command.Group
                heading="Column Types"
                className={`${GROUP_HEADING_CLASS} [&_[cmdk-group-heading]]:text-zinc-500`}
              >
                <div className="grid grid-cols-2 gap-2 px-1 pb-2">
                  <Command.Item
                    className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-zinc-800 text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:border-zinc-600 data-[selected=true]:text-white transition-all"
                    onSelect={() => {
                      onSelectAI();
                      onClose();
                    }}
                  >
                    <Brain className="w-4 h-4 text-purple-400 shrink-0" />
                    <div>
                      <div className="font-medium text-xs">Use AI</div>
                      <div className="text-[11px] text-zinc-500">
                        Natural language prompt
                      </div>
                    </div>
                  </Command.Item>
                  <Command.Item
                    className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-zinc-800 text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:border-zinc-600 data-[selected=true]:text-white transition-all"
                    onSelect={() => {
                      onSelectFormula();
                      onClose();
                    }}
                  >
                    <Calculator className="w-4 h-4 text-teal-400 shrink-0" />
                    <div>
                      <div className="font-medium text-xs">Formula</div>
                      <div className="text-[11px] text-zinc-500">
                        Computed from columns
                      </div>
                    </div>
                  </Command.Item>
                  <Command.Item
                    className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-zinc-800 text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:border-zinc-600 data-[selected=true]:text-white transition-all"
                    onSelect={() => {
                      onSelectGate();
                      onClose();
                    }}
                  >
                    <Filter className="w-4 h-4 text-amber-400 shrink-0" />
                    <div>
                      <div className="font-medium text-xs">Gate / Filter</div>
                      <div className="text-[11px] text-zinc-500">
                        Filter rows by condition
                      </div>
                    </div>
                  </Command.Item>
                  <Command.Item
                    className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-zinc-800 text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:border-zinc-600 data-[selected=true]:text-white transition-all"
                    onSelect={() => {
                      onSelectStatic();
                      onClose();
                    }}
                  >
                    <Type className="w-4 h-4 text-zinc-400 shrink-0" />
                    <div>
                      <div className="font-medium text-xs">Static Column</div>
                      <div className="text-[11px] text-zinc-500">
                        Manual text or number
                      </div>
                    </div>
                  </Command.Item>
                  {onSelectHttp && (
                    <Command.Item
                      className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-zinc-800 text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:border-zinc-600 data-[selected=true]:text-white transition-all"
                      onSelect={() => {
                        onSelectHttp();
                        onClose();
                      }}
                      value="http request api call endpoint"
                    >
                      <Unplug className="w-4 h-4 text-orange-400 shrink-0" />
                      <div>
                        <div className="font-medium text-xs">HTTP Request</div>
                        <div className="text-[11px] text-zinc-500">
                          Call any API endpoint
                        </div>
                      </div>
                    </Command.Item>
                  )}
                  {onSelectWaterfall && (
                    <Command.Item
                      className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-zinc-800 text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:border-zinc-600 data-[selected=true]:text-white transition-all"
                      onSelect={() => {
                        onSelectWaterfall();
                        onClose();
                      }}
                      value="waterfall fallback providers cascade"
                    >
                      <Shuffle className="w-4 h-4 text-emerald-400 shrink-0" />
                      <div>
                        <div className="font-medium text-xs">Waterfall</div>
                        <div className="text-[11px] text-zinc-500">
                          Try providers in order
                        </div>
                      </div>
                    </Command.Item>
                  )}
                  {onSelectLookup && (
                    <Command.Item
                      className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-zinc-800 text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:border-zinc-600 data-[selected=true]:text-white transition-all"
                      onSelect={() => {
                        onSelectLookup();
                        onClose();
                      }}
                      value="lookup join cross table search match"
                    >
                      <Link2 className="w-4 h-4 text-cyan-400 shrink-0" />
                      <div>
                        <div className="font-medium text-xs">Lookup</div>
                        <div className="text-[11px] text-zinc-500">
                          Cross-table data join
                        </div>
                      </div>
                    </Command.Item>
                  )}
                  {onSelectScript && (
                    <Command.Item
                      className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-zinc-800 text-sm text-zinc-300 cursor-pointer data-[selected=true]:bg-zinc-800 data-[selected=true]:border-zinc-600 data-[selected=true]:text-white transition-all"
                      onSelect={() => {
                        onSelectScript();
                        onClose();
                      }}
                      value="script code python bash node transform"
                    >
                      <Terminal className="w-4 h-4 text-rose-400 shrink-0" />
                      <div>
                        <div className="font-medium text-xs">Script</div>
                        <div className="text-[11px] text-zinc-500">
                          Run Python/Bash/Node code
                        </div>
                      </div>
                    </Command.Item>
                  )}
                </div>
              </Command.Group>

              {/* Tool catalog by category */}
              {[...sortedCategories, ...otherCategories].map((category) => {
                const categoryTools = grouped[category];
                const CatIcon = CATEGORY_ICONS[category] || Search;
                return (
                  <Command.Group
                    key={category}
                    heading={category}
                    className={`${GROUP_HEADING_CLASS} [&_[cmdk-group-heading]]:text-zinc-500 [&_[cmdk-group-heading]]:mt-1`}
                  >
                    {categoryTools.map((tool) => (
                      <Command.Item
                        key={tool.id}
                        className={ITEM_CLASS}
                        onSelect={() => handleSelectTool(tool)}
                        value={`${tool.name} ${tool.description} ${category}`}
                      >
                        <CatIcon className="w-4 h-4 text-blue-400 shrink-0" />
                        <div className="min-w-0 flex-1">
                          <div className="font-medium">{tool.name}</div>
                          <div className="text-xs text-zinc-500 truncate">
                            {tool.description}
                          </div>
                        </div>
                        <SpeedBadge speed={tool.speed} />
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

function SpeedBadge({ speed }: { speed?: string }) {
  if (!speed) return null;
  const color =
    speed === "fast"
      ? "bg-emerald-500/10 text-emerald-400"
      : speed === "medium"
        ? "bg-amber-500/10 text-amber-400"
        : "bg-zinc-500/10 text-zinc-400";
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${color}`}>
      {speed}
    </span>
  );
}
