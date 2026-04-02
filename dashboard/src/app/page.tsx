"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  fetchFunctions,
  fetchFolders,
  createFunction,
  deleteFunction,
  duplicateFunction,
  moveFunction,
  createFolder,
  deleteFolder,
  streamAssembleFunction,
  fetchTemplates,
  fetchToolCategories,
} from "@/lib/api";
import type { FunctionDefinition, FolderDefinition, FunctionInput, FunctionOutput, FunctionStep, ToolCategory } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Plus,
  Search,
  Folder,
  MoreHorizontal,
  GripVertical,
  Play,
  Copy,
  CopyPlus,
  Trash2,
  ChevronRight,
  Blocks,
  LayoutGrid,
  Settings2,
  Sparkles,
  ChevronDown,
  AlertTriangle,
  Zap,
  Clock,
  Brain,
  Filter,
} from "lucide-react";
import { CatalogGrid } from "@/components/functions/catalog-grid";
import { FavoritesStrip } from "@/components/functions/favorites-strip";
import { RecentRunsSection } from "@/components/functions/recent-runs-section";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { toast } from "sonner";

export default function FunctionsPage() {
  const router = useRouter();
  const [functions, setFunctions] = useState<FunctionDefinition[]>([]);
  const [folders, setFolders] = useState<FolderDefinition[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [draggedFunc, setDraggedFunc] = useState<string | null>(null);
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [showNewFolderInput, setShowNewFolderInput] = useState(false);
  const newFolderInputRef = useRef<HTMLInputElement>(null);

  // View mode: catalog (consumer) vs builder (owner)
  const [viewMode, setViewMode] = useState<"catalog" | "builder">(() => {
    if (typeof window !== "undefined") {
      return (localStorage.getItem("kiln_functions_view") as "catalog" | "builder") || "catalog";
    }
    return "catalog";
  });
  const handleToggleView = () => {
    const next = viewMode === "catalog" ? "builder" : "catalog";
    setViewMode(next);
    localStorage.setItem("kiln_functions_view", next);
  };

  // Favorites (localStorage-backed, used in catalog view)
  const [favorites, setFavorites] = useState<string[]>(() => {
    if (typeof window !== "undefined") {
      try {
        return JSON.parse(localStorage.getItem("kiln_function_favorites") || "[]");
      } catch { return []; }
    }
    return [];
  });
  const handleToggleFavorite = (id: string) => {
    setFavorites((prev) => {
      const next = prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id];
      localStorage.setItem("kiln_function_favorites", JSON.stringify(next));
      return next;
    });
  };

  const load = useCallback(async () => {
    try {
      const [funcRes, folderRes] = await Promise.all([
        fetchFunctions(searchQuery ? { q: searchQuery } : undefined),
        fetchFolders(),
      ]);
      setFunctions(funcRes.functions);
      setFolders(folderRes.folders);
    } catch (e) {
      console.error("Failed to load functions:", e);
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    load();
  }, [load]);

  // Debounced search
  const searchTimeout = useRef<NodeJS.Timeout | null>(null);
  const handleSearch = (value: string) => {
    setSearchQuery(value);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => load(), 300);
  };

  // Group functions by folder
  const functionsByFolder = useMemo(() => {
    const grouped: Record<string, FunctionDefinition[]> = {};
    for (const func of functions) {
      const folder = func.folder || "(No Folder)";
      if (!grouped[folder]) grouped[folder] = [];
      grouped[folder].push(func);
    }
    return grouped;
  }, [functions]);

  const handleCreateFunction = async () => {
    setBuilderOpen(true);
  };

  const handleDeleteFunction = async (id: string) => {
    try {
      await deleteFunction(id);
      toast.success("Function deleted");
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete function");
    }
  };

  const handleDuplicateFunction = async (func: FunctionDefinition) => {
    try {
      const copy = await duplicateFunction(func.id);
      toast.success(`Duplicated as "${copy.name}"`);
      router.push(`/functions/${copy.id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to duplicate");
    }
  };

  const handleRunFunction = (func: FunctionDefinition) => {
    router.push(`/workbench?function=${func.id}`);
  };

  const handleCopyClayConfig = (func: FunctionDefinition) => {
    const config = {
      url: `{{API_URL}}/webhook/functions/${func.id}`,
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": "{{API_KEY}}" },
      body: {
        data: Object.fromEntries(func.inputs.map(i => [i.name, `{{${i.name}}}`])),
      },
    };
    navigator.clipboard.writeText(JSON.stringify(config, null, 2));
    toast.success("Clay config copied to clipboard");
  };

  // Drag and drop handlers
  const handleDragStart = (funcId: string) => {
    setDraggedFunc(funcId);
  };

  const handleDragOver = (e: React.DragEvent, folderName: string) => {
    e.preventDefault();
    setDragOverFolder(folderName);
  };

  const handleDrop = async (folderName: string) => {
    if (draggedFunc) {
      try {
        await moveFunction(draggedFunc, folderName);
        toast.success(`Moved to ${folderName}`);
        load();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to move function");
      }
    }
    setDraggedFunc(null);
    setDragOverFolder(null);
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    try {
      await createFolder({ name: newFolderName.trim() });
      toast.success(`Folder "${newFolderName.trim()}" created`);
      setNewFolderName("");
      setShowNewFolderInput(false);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create folder");
    }
  };

  const handleToggleNewFolder = () => {
    setShowNewFolderInput(true);
    setTimeout(() => newFolderInputRef.current?.focus(), 50);
  };

  const handleDeleteFolder = async (name: string) => {
    try {
      await deleteFolder(name);
      toast.success(`Folder "${name}" deleted`);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete folder");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Functions" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        {/* Toolbar */}
        <div className="flex items-center gap-3 mb-6">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-clay-300" />
            <Input
              placeholder="Search functions..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-9 bg-clay-800 border-clay-600 text-clay-100 placeholder:text-clay-300"
            />
          </div>
          {showNewFolderInput ? (
            <div className="flex items-center gap-1.5">
              <Input
                ref={newFolderInputRef}
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreateFolder();
                  if (e.key === "Escape") { setShowNewFolderInput(false); setNewFolderName(""); }
                }}
                placeholder="Folder name..."
                className="h-8 w-40 bg-clay-800 border-clay-600 text-clay-100 text-xs"
              />
              <Button size="sm" onClick={handleCreateFolder} disabled={!newFolderName.trim()} className="h-8 bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light text-xs">
                Create
              </Button>
              <Button variant="ghost" size="sm" onClick={() => { setShowNewFolderInput(false); setNewFolderName(""); }} className="h-8 text-clay-300 text-xs">
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleNewFolder}
              className="border-clay-600 text-clay-200 hover:bg-clay-700"
            >
              <Folder className="h-4 w-4 mr-1.5" />
              New Folder
            </Button>
          )}
          <Button
            size="sm"
            onClick={handleCreateFunction}
            className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
          >
            <Plus className="h-4 w-4 mr-1.5" />
            New Function
          </Button>
          <div className="flex items-center rounded-lg border border-clay-600 p-0.5">
            <button
              onClick={() => { setViewMode("catalog"); localStorage.setItem("kiln_functions_view", "catalog"); }}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                viewMode === "catalog"
                  ? "bg-kiln-teal text-clay-950"
                  : "text-clay-300 hover:text-clay-100"
              )}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
              Sales
            </button>
            <button
              onClick={() => { setViewMode("builder"); localStorage.setItem("kiln_functions_view", "builder"); }}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                viewMode === "builder"
                  ? "bg-kiln-teal text-clay-950"
                  : "text-clay-300 hover:text-clay-100"
              )}
            >
              <Settings2 className="h-3.5 w-3.5" />
              Builder
            </button>
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-pulse text-clay-300">Loading functions...</div>
          </div>
        )}

        {/* Empty state — only when no functions AND no custom folders */}
        {!loading && functions.length === 0 && !searchQuery && folders.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="h-16 w-16 rounded-2xl bg-clay-700 flex items-center justify-center">
              <Blocks className="h-8 w-8 text-clay-300" />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-clay-100 mb-1">No functions yet</h3>
              <p className="text-sm text-clay-300 max-w-md">
                Functions are reusable data operations. Create one to enrich, score, research, or transform your data.
              </p>
            </div>
            <Button
              onClick={handleCreateFunction}
              className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
            >
              <Plus className="h-4 w-4 mr-1.5" />
              Create Your First Function
            </Button>
          </div>
        )}

        {/* Search empty state */}
        {!loading && functions.length === 0 && searchQuery && (
          <div className="flex flex-col items-center justify-center py-20 gap-2">
            <Search className="h-8 w-8 text-clay-300" />
            <p className="text-sm text-clay-300">No functions match &quot;{searchQuery}&quot;</p>
          </div>
        )}

        {/* Function grid — catalog or builder view */}
        {!loading && (functions.length > 0 || folders.length > 0) && (
          viewMode === "catalog" ? (
            <>
              <FavoritesStrip functions={functions} favoriteIds={favorites} />
              <RecentRunsSection />
              <CatalogGrid
                folders={folders}
                functionsByFolder={functionsByFolder}
                searchQuery={searchQuery}
                favorites={favorites}
                onToggleFavorite={handleToggleFavorite}
              />
            </>
          ) : (
          <div className="space-y-8">
            {folders
              .filter(f => functionsByFolder[f.name]?.length > 0 || !searchQuery)
              .map((folder) => (
              <section
                key={folder.name}
                onDragOver={(e) => handleDragOver(e, folder.name)}
                onDragLeave={() => setDragOverFolder(null)}
                onDrop={() => handleDrop(folder.name)}
                className={cn(
                  "rounded-xl p-4 transition-colors",
                  dragOverFolder === folder.name && "bg-kiln-teal/5 ring-1 ring-kiln-teal/20"
                )}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Folder className="h-4 w-4 text-clay-300" />
                    <h3 className="text-sm font-semibold text-clay-100">{folder.name}</h3>
                    <span className="text-xs text-clay-300">
                      {functionsByFolder[folder.name]?.length || 0}
                    </span>
                  </div>
                  <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-clay-300 hover:text-clay-200">
                          <MoreHorizontal className="h-3.5 w-3.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="bg-clay-800 border-clay-600">
                        <DropdownMenuItem
                          onClick={() => handleDeleteFolder(folder.name)}
                          className="text-red-400 focus:text-red-300"
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-2" />
                          Delete Folder
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                  {(functionsByFolder[folder.name] || []).map((func) => (
                    <Card
                      key={func.id}
                      draggable
                      onDragStart={() => handleDragStart(func.id)}
                      onDragEnd={() => { setDraggedFunc(null); setDragOverFolder(null); }}
                      className={cn(
                        "border-clay-600 hover:border-clay-500 cursor-pointer group transition-all",
                        draggedFunc === func.id && "opacity-50"
                      )}
                      onClick={() => router.push(`/functions/${func.id}`)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <GripVertical className="h-3.5 w-3.5 text-clay-300 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
                            <h4 className="text-sm font-medium text-clay-100 line-clamp-1">{func.name}</h4>
                          </div>
                          <ChevronRight className="h-3.5 w-3.5 text-clay-300 group-hover:text-clay-300 transition-colors" />
                        </div>
                        {func.description && (
                          <p className="text-xs text-clay-300 line-clamp-2 mb-3">{func.description}</p>
                        )}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3 text-[10px] text-clay-300">
                            <span>{func.inputs.length} inputs</span>
                            <span>{func.outputs.length} outputs</span>
                            <span>{func.steps.length} steps</span>
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-clay-300 hover:text-clay-200"
                              onClick={(e) => { e.stopPropagation(); handleDuplicateFunction(func); }}
                              title="Duplicate"
                            >
                              <CopyPlus className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-clay-300 hover:text-clay-200"
                              onClick={(e) => { e.stopPropagation(); handleCopyClayConfig(func); }}
                              title="Copy Clay config"
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-kiln-teal hover:text-kiln-teal-light"
                              onClick={(e) => { e.stopPropagation(); handleRunFunction(func); }}
                            >
                              <Play className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </section>
            ))}
          </div>
          )
        )}
      </div>

      {/* Builder slide-out panel */}
      <FunctionBuilderPanel
        open={builderOpen}
        onOpenChange={setBuilderOpen}
        folders={folders}
        onCreated={() => { setBuilderOpen(false); load(); }}
      />
    </div>
  );
}

function FunctionBuilderPanel({
  open,
  onOpenChange,
  folders: availableFolders,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  folders: FolderDefinition[];
  onCreated: () => void;
}) {
  const [step, setStep] = useState<"describe" | "streaming" | "review">("describe");
  const [prompt, setPrompt] = useState("");
  const [saving, setSaving] = useState(false);
  const [streamText, setStreamText] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  // Reasoning from AI
  const [reasoning, setReasoning] = useState<{
    thought_process?: string;
    tools_considered?: Array<{ tool_id: string; name: string; why: string; selected: boolean }>;
    confidence?: number;
  }>({});
  const [assemblyWarnings, setAssemblyWarnings] = useState<string[]>([]);
  const [assemblyDuration, setAssemblyDuration] = useState(0);
  const [reasoningOpen, setReasoningOpen] = useState(false);

  // Templates
  const [templates, setTemplates] = useState<Array<{
    id: string; name: string; description: string; category: string;
    inputs: FunctionInput[]; outputs: FunctionOutput[]; steps: FunctionStep[];
  }>>([]);
  const [showTemplates, setShowTemplates] = useState(true);

  // Editable suggestion fields
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [folder, setFolder] = useState("");
  const [inputs, setInputs] = useState<FunctionInput[]>([]);
  const [outputs, setOutputs] = useState<FunctionOutput[]>([]);
  const [steps, setSteps] = useState<FunctionStep[]>([]);

  // Tool catalog for step adding
  const [toolCategories, setToolCategories] = useState<ToolCategory[]>([]);
  const [showAddStep, setShowAddStep] = useState(false);

  // Load templates + tool catalog on mount
  useEffect(() => {
    fetchTemplates().then((res) => setTemplates(res.templates)).catch(() => {});
    fetchToolCategories().then((res) => setToolCategories(res.categories)).catch(() => {});
  }, []);

  const handleAssemble = () => {
    if (!prompt.trim()) {
      toast.error("Describe what you want the function to do");
      return;
    }
    setStreamText("");
    setReasoning({});
    setAssemblyWarnings([]);
    setStep("streaming");

    abortRef.current = streamAssembleFunction(
      { description: prompt },
      {
        onChunk: (text) => setStreamText((prev) => prev + text),
        onComplete: (result) => {
          const s = result.suggestion as Record<string, unknown>;
          setName(String(s.name || ""));
          setDescription(String(s.description || ""));
          setInputs((s.inputs as FunctionInput[]) || []);
          setOutputs((s.outputs as FunctionOutput[]) || []);
          setSteps((s.steps as FunctionStep[]) || []);
          setReasoning(result.reasoning as typeof reasoning);
          setAssemblyWarnings(result.warnings || []);
          setAssemblyDuration(result.duration_ms);
          setStep("review");
        },
        onError: (msg) => {
          toast.error(msg);
          setStep("describe");
        },
      }
    );
  };

  const handleUseTemplate = (tpl: typeof templates[0]) => {
    setName(tpl.name);
    setDescription(tpl.description);
    setInputs(tpl.inputs as FunctionInput[]);
    setOutputs(tpl.outputs as FunctionOutput[]);
    setSteps(tpl.steps as FunctionStep[]);
    setReasoning({});
    setAssemblyWarnings([]);
    setStep("review");
  };

  const handleCancel = () => {
    if (abortRef.current) abortRef.current.abort();
    onOpenChange(false);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error("Function name is required");
      return;
    }
    if (!folder) {
      toast.error("Select a folder for this function");
      return;
    }
    setSaving(true);
    try {
      const cleanInputs = inputs.filter(inp => inp.name.trim());
      const cleanOutputs = outputs.filter(out => out.key.trim());
      await createFunction({ name, description, folder, inputs: cleanInputs, outputs: cleanOutputs, steps });
      toast.success(`Function "${name}" created`);
      onCreated();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create function");
    } finally {
      setSaving(false);
    }
  };

  const handleRegenerate = () => {
    setStep("describe");
  };

  // Input CRUD
  const handleAddInput = () => setInputs([...inputs, { name: "", type: "string", required: false, description: "" }]);
  const handleRemoveInput = (i: number) => setInputs(inputs.filter((_, idx) => idx !== i));
  const handleUpdateInput = (i: number, field: keyof FunctionInput, value: string | boolean) =>
    setInputs(inputs.map((inp, idx) => idx === i ? { ...inp, [field]: value } : inp));

  // Output CRUD
  const handleAddOutput = () => setOutputs([...outputs, { key: "", type: "string", description: "" }]);
  const handleRemoveOutput = (i: number) => setOutputs(outputs.filter((_, idx) => idx !== i));
  const handleUpdateOutput = (i: number, field: keyof FunctionOutput, value: string) =>
    setOutputs(outputs.map((out, idx) => idx === i ? { ...out, [field]: value } : out));

  // Speed icon helper
  const speedIcon = (tool: string) => {
    if (tool === "gate") return <Filter className="h-3 w-3 text-amber-400" />;
    if (tool.startsWith("function:")) return <Blocks className="h-3 w-3 text-indigo-400" />;
    if (tool === "findymail") return <Zap className="h-3 w-3 text-emerald-400" />;
    const agentTools = ["exa", "crustdata", "google_search", "apollo_people", "dropleads", "peopledatalabs", "apollo_org", "leadmagic", "parallel", "firecrawl", "apify", "scrapegraph", "web_search"];
    if (agentTools.includes(tool)) return <Clock className="h-3 w-3 text-amber-400" />;
    return <Brain className="h-3 w-3 text-blue-400" />;
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:w-[520px] sm:max-w-[520px] p-0 flex flex-col">
        <SheetHeader className="p-4 border-b border-clay-600">
          <SheetTitle>New Function</SheetTitle>
        </SheetHeader>

      {/* Step 1: Describe */}
      {step === "describe" && (
        <>
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {/* Templates */}
            {templates.length > 0 && (
              <div>
                <button
                  onClick={() => setShowTemplates(!showTemplates)}
                  className="flex items-center gap-1.5 text-xs font-medium text-clay-300 hover:text-clay-100 mb-2"
                >
                  <Sparkles className="h-3.5 w-3.5 text-kiln-teal" />
                  Start from template
                  <ChevronDown className={cn("h-3 w-3 transition-transform", showTemplates && "rotate-180")} />
                </button>
                {showTemplates && (
                  <div className="grid grid-cols-2 gap-2 mb-3">
                    {templates.map((tpl) => (
                      <button
                        key={tpl.id}
                        onClick={() => handleUseTemplate(tpl)}
                        className="text-left p-2.5 rounded-lg bg-clay-900/50 border border-clay-700 hover:border-kiln-teal/50 hover:bg-clay-800/50 transition-colors"
                      >
                        <div className="text-xs font-medium text-clay-100 mb-0.5">{tpl.name}</div>
                        <div className="text-[10px] text-clay-300 line-clamp-2">{tpl.description}</div>
                        <div className="flex gap-1 mt-1.5">
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-clay-700/50 text-clay-300">{tpl.inputs.length} in</span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-clay-700/50 text-clay-300">{tpl.outputs.length} out</span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-clay-700/50 text-clay-300">{tpl.steps.length} steps</span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="bg-clay-900/50 border border-clay-700 rounded-lg p-4">
              <div className="text-sm font-medium text-clay-100 mb-1">Describe your function</div>
              <p className="text-xs text-clay-300 mb-3">
                Tell me what data you want in and what results you want out. I&apos;ll suggest the right tools and build the function for you.
              </p>
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={"e.g., Given a company name, find their domain, look up their tech stack, find the VP of Sales email, and verify the email is valid."}
                rows={5}
                autoFocus
                className="resize-none"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAssemble();
                }}
              />
              <div className="text-[10px] text-clay-300 mt-1">Press Cmd+Enter to submit</div>
            </div>

            <div>
              <label className="text-xs font-medium text-clay-300 mb-1 block">Folder <span className="text-red-400">*</span></label>
              <Select value={folder} onValueChange={setFolder}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a folder..." />
                </SelectTrigger>
                <SelectContent>
                  {availableFolders.map(f => (
                    <SelectItem key={f.name} value={f.name}>{f.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {availableFolders.length === 0 && (
                <p className="text-[10px] text-clay-300 mt-1">No folders yet — create one first using the &quot;New Folder&quot; button above</p>
              )}
            </div>

            <div className="border-t border-clay-700 pt-3">
              <button
                onClick={() => { setName(""); setDescription(""); setStep("review"); }}
                className="text-xs text-clay-300 hover:text-clay-200 underline"
              >
                Skip AI — build manually instead
              </button>
            </div>
          </div>

          <div className="p-4 border-t border-clay-600 flex items-center gap-2 justify-end">
            <Button variant="outline" onClick={handleCancel} className="border-clay-600 text-clay-300">
              Cancel
            </Button>
            <Button
              onClick={handleAssemble}
              disabled={!prompt.trim()}
              className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
            >
              <Sparkles className="h-3.5 w-3.5 mr-1.5" />
              Build Function
            </Button>
          </div>
        </>
      )}

      {/* Step 1.5: Streaming AI response */}
      {step === "streaming" && (
        <>
          <div className="flex-1 overflow-auto p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="h-3 w-3 border-2 border-kiln-teal/30 border-t-kiln-teal rounded-full animate-spin" />
              <span className="text-sm font-medium text-clay-100">Building your function...</span>
            </div>
            <div className="bg-clay-900/50 border border-clay-700 rounded-lg p-4 font-mono text-xs text-clay-300 whitespace-pre-wrap max-h-[60vh] overflow-auto">
              {streamText || "Analyzing your request..."}
              <span className="inline-block w-1.5 h-3.5 bg-kiln-teal/70 animate-pulse ml-0.5" />
            </div>
          </div>
          <div className="p-4 border-t border-clay-600 flex items-center gap-2 justify-end">
            <Button variant="outline" onClick={() => { if (abortRef.current) abortRef.current.abort(); setStep("describe"); }} className="border-clay-600 text-clay-300">
              Cancel
            </Button>
          </div>
        </>
      )}

      {/* Step 2: Review & Edit */}
      {step === "review" && (
        <>
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {/* AI Reasoning Panel (collapsible) */}
            {reasoning.thought_process && (
              <div className="bg-clay-900/30 border border-clay-700 rounded-lg overflow-hidden">
                <button
                  onClick={() => setReasoningOpen(!reasoningOpen)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-clay-800/30 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Brain className="h-3.5 w-3.5 text-blue-400" />
                    <span className="text-clay-200 font-medium">AI Reasoning</span>
                    {reasoning.confidence != null && (
                      <span className={cn(
                        "px-1.5 py-0.5 rounded text-[10px] font-medium",
                        reasoning.confidence >= 0.8 ? "bg-emerald-500/15 text-emerald-400" :
                        reasoning.confidence >= 0.5 ? "bg-amber-500/15 text-amber-400" :
                        "bg-red-500/15 text-red-400"
                      )}>
                        {Math.round(reasoning.confidence * 100)}% confidence
                      </span>
                    )}
                    {assemblyDuration > 0 && (
                      <span className="text-[10px] text-clay-400">{(assemblyDuration / 1000).toFixed(1)}s</span>
                    )}
                  </div>
                  <ChevronDown className={cn("h-3.5 w-3.5 text-clay-400 transition-transform", reasoningOpen && "rotate-180")} />
                </button>
                {reasoningOpen && (
                  <div className="px-3 pb-3 space-y-2 border-t border-clay-700/50">
                    <p className="text-xs text-clay-300 mt-2">{reasoning.thought_process}</p>
                    {reasoning.tools_considered && reasoning.tools_considered.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-[10px] text-clay-400 font-medium">Tools considered:</div>
                        {reasoning.tools_considered.map((t, i) => (
                          <div key={i} className="flex items-center gap-2 text-[10px]">
                            <span className={cn(
                              "w-1.5 h-1.5 rounded-full",
                              t.selected ? "bg-emerald-400" : "bg-clay-500"
                            )} />
                            <span className={t.selected ? "text-clay-100" : "text-clay-400"}>{t.name}</span>
                            <span className="text-clay-500">—</span>
                            <span className="text-clay-400">{t.why}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Validation Warnings */}
            {assemblyWarnings.length > 0 && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">
                <div className="flex items-center gap-1.5 text-xs text-amber-400 font-medium mb-1">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Validation warnings
                </div>
                {assemblyWarnings.map((w, i) => (
                  <div key={i} className="text-[10px] text-amber-300/80">{w}</div>
                ))}
              </div>
            )}

            {/* Name & Description */}
            <div>
              <label className="text-xs font-medium text-clay-300 mb-1 block">Name</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Enrich Company Data"
                className="bg-clay-900 border-clay-600 text-clay-100"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-clay-300 mb-1 block">Description</label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What does this function do?"
                rows={2}
              />
            </div>

            {/* Folder */}
            <div>
              <label className="text-xs font-medium text-clay-300 mb-1 block">Folder <span className="text-red-400">*</span></label>
              <Select value={folder} onValueChange={setFolder}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a folder..." />
                </SelectTrigger>
                <SelectContent>
                  {availableFolders.map(f => (
                    <SelectItem key={f.name} value={f.name}>{f.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {availableFolders.length === 0 && (
                <p className="text-[10px] text-clay-300 mt-1">No folders yet — create one first using the &quot;New Folder&quot; button above</p>
              )}
            </div>

            {/* Inputs */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs font-medium text-clay-300">Inputs ({inputs.length})</div>
                <button onClick={handleAddInput} className="flex items-center gap-1 text-[10px] text-clay-300 hover:text-clay-100">
                  <Plus className="h-3 w-3" /> Add
                </button>
              </div>
              <div className="space-y-1">
                {inputs.map((inp, i) => (
                  <div key={i} className="group flex items-center gap-1.5 px-2 py-1 rounded bg-clay-900/50 border border-clay-700 text-xs">
                    <Input
                      value={inp.name}
                      onChange={(e) => handleUpdateInput(i, "name", e.target.value)}
                      placeholder="field_name"
                      className="h-6 flex-1 bg-transparent border-0 px-1 text-xs text-clay-100 focus-visible:ring-0"
                    />
                    <Select value={inp.type} onValueChange={(v) => handleUpdateInput(i, "type", v)}>
                      <SelectTrigger className="h-6 w-[72px] bg-transparent border-0 px-1 text-[10px] text-clay-300 focus:ring-0">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {["string", "number", "url", "email", "boolean"].map(t => (
                          <SelectItem key={t} value={t} className="text-xs">{t}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Checkbox
                      checked={inp.required}
                      onCheckedChange={(v) => handleUpdateInput(i, "required", !!v)}
                      className="h-3.5 w-3.5"
                    />
                    <span className="text-[10px] text-clay-300">req</span>
                    <button
                      onClick={() => handleRemoveInput(i)}
                      className="opacity-0 group-hover:opacity-100 text-clay-300 hover:text-red-400 transition-opacity"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
                {inputs.length === 0 && <div className="text-xs text-clay-300 py-1">No inputs yet</div>}
              </div>
            </div>

            {/* Outputs */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs font-medium text-clay-300">Outputs ({outputs.length})</div>
                <button onClick={handleAddOutput} className="flex items-center gap-1 text-[10px] text-clay-300 hover:text-clay-100">
                  <Plus className="h-3 w-3" /> Add
                </button>
              </div>
              <div className="space-y-1">
                {outputs.map((out, i) => (
                  <div key={i} className="group flex items-center gap-1.5 px-2 py-1 rounded bg-clay-900/50 border border-clay-700 text-xs">
                    <Input
                      value={out.key}
                      onChange={(e) => handleUpdateOutput(i, "key", e.target.value)}
                      placeholder="output_key"
                      className="h-6 flex-1 bg-transparent border-0 px-1 text-xs text-kiln-teal focus-visible:ring-0"
                    />
                    <Select value={out.type} onValueChange={(v) => handleUpdateOutput(i, "type", v)}>
                      <SelectTrigger className="h-6 w-[72px] bg-transparent border-0 px-1 text-[10px] text-clay-300 focus:ring-0">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {["string", "number", "boolean", "json"].map(t => (
                          <SelectItem key={t} value={t} className="text-xs">{t}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <button
                      onClick={() => handleRemoveOutput(i)}
                      className="opacity-0 group-hover:opacity-100 text-clay-300 hover:text-red-400 transition-opacity"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
                {outputs.length === 0 && <div className="text-xs text-clay-300 py-1">No outputs yet</div>}
              </div>
            </div>

            {/* Steps with speed indicators */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs font-medium text-clay-300">Steps ({steps.length})</div>
                <button
                  onClick={() => setShowAddStep(!showAddStep)}
                  className="flex items-center gap-1 text-[10px] text-clay-300 hover:text-clay-100"
                >
                  <Plus className="h-3 w-3" /> Add Step
                </button>
              </div>

              {/* Add step picker */}
              {showAddStep && (
                <div className="mb-2 bg-clay-900/80 border border-clay-600 rounded-lg p-2 max-h-48 overflow-auto space-y-2">
                  {toolCategories
                    .filter(cat => ["Flow Control", "Functions", "AI Processing", "Recommended", "Research", "People Search", "Email Finding", "Company Enrichment", "Scraping"].includes(cat.category))
                    .sort((a, b) => {
                      const order = ["Flow Control", "Functions", "AI Processing", "Recommended"];
                      const ai = order.indexOf(a.category);
                      const bi = order.indexOf(b.category);
                      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
                    })
                    .map(cat => (
                    <div key={cat.category}>
                      <div className="text-[10px] text-clay-400 font-medium mb-1">{cat.category}</div>
                      <div className="flex flex-wrap gap-1">
                        {cat.tools.map(tool => (
                          <button
                            key={tool.id}
                            onClick={() => {
                              const params: Record<string, string> = {};
                              for (const inp of tool.inputs) params[inp.name] = "";
                              setSteps([...steps, { tool: tool.id, params }]);
                              setShowAddStep(false);
                            }}
                            className={cn(
                              "text-[10px] px-2 py-1 rounded border transition-colors",
                              tool.id === "gate"
                                ? "border-amber-700/50 bg-amber-950/30 text-amber-300 hover:bg-amber-900/40"
                                : tool.source === "function"
                                  ? "border-indigo-700/40 bg-indigo-950/20 text-indigo-300 hover:bg-indigo-900/30"
                                  : "border-clay-600 bg-clay-800/50 text-clay-200 hover:bg-clay-700/50"
                            )}
                          >
                            {tool.name}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="space-y-1">
                {steps.map((s, i) => (
                  <div
                    key={i}
                    className={cn(
                      "group flex items-center gap-2 px-2 py-1.5 rounded border text-xs",
                      s.tool === "gate"
                        ? "bg-amber-950/30 border-amber-700/50"
                        : s.tool.startsWith("function:")
                          ? "bg-indigo-950/20 border-indigo-700/40"
                          : "bg-clay-900/50 border-clay-700"
                    )}
                  >
                    <span className="text-clay-300 w-4">{i + 1}</span>
                    {speedIcon(s.tool)}
                    <span className="font-medium text-clay-100 flex-1">{s.tool}</span>
                    {/* Editable params for gate condition */}
                    {s.tool === "gate" && (
                      <Input
                        value={s.params.condition || ""}
                        onChange={(e) => {
                          const updated = [...steps];
                          updated[i] = { ...updated[i], params: { ...updated[i].params, condition: e.target.value } };
                          setSteps(updated);
                        }}
                        placeholder="e.g. qualified == 'Y'"
                        className="h-5 w-40 bg-transparent border-0 px-1 text-[10px] text-amber-300 focus-visible:ring-0 placeholder:text-amber-800"
                      />
                    )}
                    <button
                      onClick={() => setSteps(steps.filter((_, idx) => idx !== i))}
                      className="opacity-0 group-hover:opacity-100 text-clay-300 hover:text-red-400 transition-opacity"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
                {steps.length === 0 && <div className="text-xs text-clay-300 py-1">No steps yet — click &quot;+ Add Step&quot; above</div>}
              </div>
              {steps.length > 0 && (
                <div className="flex items-center gap-3 mt-2 text-[10px] text-clay-400">
                  <span className="flex items-center gap-1"><Zap className="h-2.5 w-2.5 text-emerald-400" /> fast (native)</span>
                  <span className="flex items-center gap-1"><Brain className="h-2.5 w-2.5 text-blue-400" /> medium (AI)</span>
                  <span className="flex items-center gap-1"><Clock className="h-2.5 w-2.5 text-amber-400" /> slow (web search)</span>
                  <span className="flex items-center gap-1"><Filter className="h-2.5 w-2.5 text-amber-400" /> gate</span>
                  <span className="flex items-center gap-1"><Blocks className="h-2.5 w-2.5 text-indigo-400" /> function</span>
                </div>
              )}
            </div>
          </div>

          <div className="p-4 border-t border-clay-600 flex items-center justify-between">
            <Button variant="ghost" size="sm" onClick={handleRegenerate} className="text-clay-300 text-xs">
              Regenerate
            </Button>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={handleCancel} className="border-clay-600 text-clay-300">
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving || !name.trim() || !folder}
                className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
              >
                {saving ? "Creating..." : "Create Function"}
              </Button>
            </div>
          </div>
        </>
      )}
    </SheetContent>
    </Sheet>
  );
}
