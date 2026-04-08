"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Plus, Table2, Upload, Trash2, MoreVertical, Layers, Search, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog as DialogPrimitive } from "radix-ui";
import { toast } from "sonner";
import { fetchTables, createTable, deleteTable, importTableCsv, fetchFunctions, getOrCreateFunctionTable, addTableColumn } from "@/lib/api";
import type { TableSummary, FunctionDefinition, WorkflowTemplate } from "@/lib/types";
import { AiBuilderDialog } from "@/components/table-builder/ai-builder-dialog";
import { TemplateGallery } from "@/components/templates/template-gallery";
import Papa from "papaparse";

export default function TablesPageWrapper() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-clay-950 flex items-center justify-center text-clay-200">Loading...</div>}>
      <TablesPage />
    </Suspense>
  );
}

function TablesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);
  const [funcPickerOpen, setFuncPickerOpen] = useState(false);
  const [functions, setFunctions] = useState<FunctionDefinition[]>([]);
  const [funcSearch, setFuncSearch] = useState("");
  const [aiBuilderOpen, setAiBuilderOpen] = useState(false);
  const [creatingFromTemplate, setCreatingFromTemplate] = useState(false);

  useEffect(() => {
    fetchTables()
      .then((r) => setTables(r.tables))
      .catch(() => toast.error("Failed to load tables"))
      .finally(() => setLoading(false));
  }, []);

  // Handle URL actions from homepage quick actions
  useEffect(() => {
    const action = searchParams.get("action");
    if (action === "import") {
      // Small delay so the page renders first
      setTimeout(() => fileRef.current?.click(), 200);
    } else if (action === "ai-builder") {
      setAiBuilderOpen(true);
    }
  }, [searchParams]);

  const handleCreate = async () => {
    try {
      const table = await createTable({ name: "Untitled Table" });
      router.push(`/tables/${table.id}`);
    } catch {
      toast.error("Failed to create table");
    }
  };

  const handleImportCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      // Create table from filename
      const name = file.name.replace(/\.csv$/i, "").replace(/[_-]/g, " ");
      const table = await createTable({ name });
      await importTableCsv(table.id, file);
      toast.success(`Imported ${name}`);
      router.push(`/tables/${table.id}`);
    } catch {
      toast.error("Failed to import CSV");
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleNewFromFunction = async () => {
    try {
      const res = await fetchFunctions();
      setFunctions(res.functions);
      setFuncSearch("");
      setFuncPickerOpen(true);
    } catch {
      toast.error("Failed to load functions");
    }
  };

  const handleSelectFunction = async (func: FunctionDefinition) => {
    setFuncPickerOpen(false);
    try {
      const table = await getOrCreateFunctionTable(func.id);
      toast.success(`Created table from "${func.name}"`);
      router.push(`/tables/${table.id}`);
    } catch {
      toast.error("Failed to create table from function");
    }
  };

  const handleAIBuildColumns = async (
    tableName: string,
    columns: Array<{
      name: string;
      id: string;
      column_type: string;
      tool?: string;
      params?: Record<string, string>;
      ai_prompt?: string;
      ai_model?: string;
      condition?: string;
      formula?: string;
    }>,
  ) => {
    try {
      const table = await createTable({ name: tableName });
      // Add each column sequentially
      for (const col of columns) {
        await addTableColumn(table.id, {
          name: col.name,
          column_type: col.column_type,
          tool: col.tool,
          params: col.params,
          ai_prompt: col.ai_prompt,
          ai_model: col.ai_model,
          condition: col.condition,
          formula: col.formula,
        });
      }
      toast.success(`Created "${tableName}" with ${columns.length} columns`);
      router.push(`/tables/${table.id}`);
    } catch {
      toast.error("Failed to create table");
    }
  };

  const handleSelectTemplate = async (template: WorkflowTemplate) => {
    if (creatingFromTemplate) return;
    setCreatingFromTemplate(true);
    try {
      const table = await createTable({ name: template.name });
      for (const col of template.columns) {
        await addTableColumn(table.id, {
          name: col.name,
          column_type: col.column_type,
          tool: col.tool,
          params: col.params,
          ai_prompt: col.ai_prompt,
          ai_model: col.ai_model,
        });
      }
      toast.success(`Created "${template.name}" table — upload a CSV to get started`);
      router.push(`/tables/${table.id}`);
    } catch {
      toast.error("Failed to create table from template");
    } finally {
      setCreatingFromTemplate(false);
    }
  };

  const filteredFunctions = funcSearch
    ? functions.filter(
        (f) =>
          f.name.toLowerCase().includes(funcSearch.toLowerCase()) ||
          f.description.toLowerCase().includes(funcSearch.toLowerCase()),
      )
    : functions;

  const handleDelete = async (id: string) => {
    try {
      await deleteTable(id);
      setTables((prev) => prev.filter((t) => t.id !== id));
      toast.success("Table deleted");
    } catch {
      toast.error("Failed to delete table");
    }
  };

  const formatDate = (ts: number) =>
    new Date(ts * 1000).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });

  return (
    <div className="min-h-screen bg-clay-950 text-white p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2">
              <Table2 className="w-6 h-6 text-kiln-teal" />
              Tables
            </h1>
            <p className="text-clay-200 text-sm mt-1">
              Clay-style enrichment tables. Import data, add columns, watch results fill in.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={handleImportCsv}
            />
            <Button
              variant="outline"
              className="border-clay-500 text-clay-100 hover:bg-clay-700"
              onClick={() => fileRef.current?.click()}
            >
              <Upload className="w-4 h-4 mr-2" />
              Import CSV
            </Button>
            <Button
              variant="outline"
              className="border-clay-500 text-clay-100 hover:bg-clay-700"
              onClick={handleNewFromFunction}
            >
              <Layers className="w-4 h-4 mr-2" />
              From Function
            </Button>
            <Button
              variant="outline"
              className="border-purple-500/30 text-purple-300 hover:bg-purple-500/10 hover:border-purple-500/50"
              onClick={() => setAiBuilderOpen(true)}
            >
              <Sparkles className="w-4 h-4 mr-2" />
              AI Builder
            </Button>
            <Button
              className="bg-kiln-teal text-black hover:bg-kiln-teal/90"
              onClick={handleCreate}
            >
              <Plus className="w-4 h-4 mr-2" />
              New Table
            </Button>
          </div>
        </div>

        {/* Template Gallery */}
        <div className="mb-8">
          <TemplateGallery
            onSelect={handleSelectTemplate}
            compact
          />
        </div>

        {/* Table Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-32 rounded-lg bg-clay-900 border border-clay-700 animate-pulse"
              />
            ))}
          </div>
        ) : tables.length === 0 ? (
          <div className="text-center py-20">
            <Table2 className="w-12 h-12 text-clay-500 mx-auto mb-4" />
            <p className="text-clay-200 text-lg mb-2">No tables yet</p>
            <p className="text-clay-300 text-sm mb-6">
              Create a new table or import a CSV to get started
            </p>
            <div className="flex gap-2 justify-center">
              <Button
                variant="outline"
                className="border-clay-500 text-clay-100"
                onClick={() => fileRef.current?.click()}
              >
                <Upload className="w-4 h-4 mr-2" />
                Import CSV
              </Button>
              <Button
                className="bg-kiln-teal text-black"
                onClick={handleCreate}
              >
                <Plus className="w-4 h-4 mr-2" />
                New Table
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {tables.map((t) => (
              <div
                key={t.id}
                className="group rounded-lg bg-clay-900 border border-clay-700 hover:border-clay-400 transition-colors cursor-pointer p-4"
                onClick={() => router.push(`/tables/${t.id}`)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-white truncate">{t.name}</h3>
                    {t.description && (
                      <p className="text-clay-300 text-sm mt-1 truncate">{t.description}</p>
                    )}
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 opacity-0 group-hover:opacity-100 text-clay-200"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="bg-clay-900 border-clay-500">
                      <DropdownMenuItem
                        className="text-red-400 focus:text-red-400"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(t.id);
                        }}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <div className="flex items-center gap-4 mt-4 text-xs text-clay-300">
                  <span>{t.row_count} rows</span>
                  <span>{t.column_count} columns</span>
                  <span className="ml-auto">{formatDate(t.updated_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Function picker dialog */}
      <DialogPrimitive.Root open={funcPickerOpen} onOpenChange={(o) => !o && setFuncPickerOpen(false)}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 bg-black/60 z-50" />
          <DialogPrimitive.Content className="fixed top-[15%] left-1/2 -translate-x-1/2 w-full max-w-lg z-50 bg-clay-900 border border-clay-500 rounded-lg shadow-2xl overflow-hidden">
            <DialogPrimitive.Title className="sr-only">Choose a function</DialogPrimitive.Title>
            <DialogPrimitive.Description className="sr-only">
              Select a function to create a table from
            </DialogPrimitive.Description>

            <div className="border-b border-clay-700 px-4 py-3 flex items-center gap-3">
              <Search className="w-4 h-4 text-clay-300 shrink-0" />
              <input
                value={funcSearch}
                onChange={(e) => setFuncSearch(e.target.value)}
                placeholder="Search functions..."
                className="flex-1 bg-transparent text-white text-sm outline-none placeholder:text-clay-300"
                autoFocus
              />
            </div>

            <div className="max-h-80 overflow-y-auto p-2">
              {filteredFunctions.length === 0 ? (
                <p className="text-center text-sm text-clay-300 py-8">
                  {functions.length === 0 ? "No functions found" : "No matching functions"}
                </p>
              ) : (
                filteredFunctions.map((func) => (
                  <button
                    key={func.id}
                    className="w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left hover:bg-clay-700 transition-colors"
                    onClick={() => handleSelectFunction(func)}
                  >
                    <Layers className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-white truncate">{func.name}</div>
                      {func.description && (
                        <div className="text-xs text-clay-300 truncate mt-0.5">{func.description}</div>
                      )}
                      <div className="flex gap-3 mt-1 text-[10px] text-clay-300">
                        <span>{func.inputs.length} inputs</span>
                        <span>{func.steps.length} steps</span>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>

      {/* AI Builder dialog */}
      <AiBuilderDialog
        open={aiBuilderOpen}
        onClose={() => setAiBuilderOpen(false)}
        onApplyColumns={handleAIBuildColumns}
      />
    </div>
  );
}
