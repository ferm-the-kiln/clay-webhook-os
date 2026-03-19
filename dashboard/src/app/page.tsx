"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  fetchFunctions,
  fetchFolders,
  createFunction,
  deleteFunction,
  moveFunction,
  createFolder,
  deleteFolder,
} from "@/lib/api";
import type { FunctionDefinition, FolderDefinition } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Plus,
  Search,
  Folder,
  MoreHorizontal,
  GripVertical,
  Play,
  Copy,
  Trash2,
  ChevronRight,
  Blocks,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  const functionsByFolder: Record<string, FunctionDefinition[]> = {};
  for (const func of functions) {
    const folder = func.folder || "Uncategorized";
    if (!functionsByFolder[folder]) functionsByFolder[folder] = [];
    functionsByFolder[folder].push(func);
  }

  const handleCreateFunction = async () => {
    setBuilderOpen(true);
  };

  const handleDeleteFunction = async (id: string) => {
    try {
      await deleteFunction(id);
      toast.success("Function deleted");
      load();
    } catch {
      toast.error("Failed to delete function");
    }
  };

  const handleRunFunction = (func: FunctionDefinition) => {
    router.push(`/workbench?function=${func.id}`);
  };

  const handleCopyClayConfig = (func: FunctionDefinition) => {
    const config = {
      url: `{{API_URL}}/webhook`,
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": "{{API_KEY}}" },
      body: {
        function: func.id,
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
      } catch {
        toast.error("Failed to move function");
      }
    }
    setDraggedFunc(null);
    setDragOverFolder(null);
  };

  const handleCreateFolder = async () => {
    const name = prompt("Folder name:");
    if (!name?.trim()) return;
    try {
      await createFolder({ name: name.trim() });
      toast.success(`Folder "${name}" created`);
      load();
    } catch {
      toast.error("Failed to create folder");
    }
  };

  const handleDeleteFolder = async (name: string) => {
    try {
      await deleteFolder(name);
      toast.success(`Folder "${name}" deleted`);
      load();
    } catch {
      toast.error("Failed to delete folder");
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
              className="pl-9 bg-clay-800 border-clay-600 text-clay-100 placeholder:text-clay-400"
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCreateFolder}
            className="border-clay-600 text-clay-200 hover:bg-clay-700"
          >
            <Folder className="h-4 w-4 mr-1.5" />
            New Folder
          </Button>
          <Button
            size="sm"
            onClick={handleCreateFunction}
            className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
          >
            <Plus className="h-4 w-4 mr-1.5" />
            New Function
          </Button>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-pulse text-clay-300">Loading functions...</div>
          </div>
        )}

        {/* Empty state */}
        {!loading && functions.length === 0 && !searchQuery && (
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
            <Search className="h-8 w-8 text-clay-400" />
            <p className="text-sm text-clay-300">No functions match &quot;{searchQuery}&quot;</p>
          </div>
        )}

        {/* Folder grid */}
        {!loading && functions.length > 0 && (
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
                    <span className="text-xs text-clay-400">
                      {functionsByFolder[folder.name]?.length || 0}
                    </span>
                  </div>
                  {folder.name !== "Uncategorized" && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-clay-400 hover:text-clay-200">
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
                  )}
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
                            <GripVertical className="h-3.5 w-3.5 text-clay-500 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
                            <h4 className="text-sm font-medium text-clay-100 line-clamp-1">{func.name}</h4>
                          </div>
                          <ChevronRight className="h-3.5 w-3.5 text-clay-500 group-hover:text-clay-300 transition-colors" />
                        </div>
                        {func.description && (
                          <p className="text-xs text-clay-300 line-clamp-2 mb-3">{func.description}</p>
                        )}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3 text-[10px] text-clay-400">
                            <span>{func.inputs.length} inputs</span>
                            <span>{func.outputs.length} outputs</span>
                            <span>{func.steps.length} steps</span>
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-clay-400 hover:text-clay-200"
                              onClick={(e) => { e.stopPropagation(); handleCopyClayConfig(func); }}
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
        )}
      </div>

      {/* Builder slide-out panel (Phase 4 — placeholder) */}
      {builderOpen && (
        <FunctionBuilderPanel
          onClose={() => setBuilderOpen(false)}
          onCreated={() => { setBuilderOpen(false); load(); }}
        />
      )}
    </div>
  );
}

function FunctionBuilderPanel({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [folder, setFolder] = useState("Uncategorized");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error("Function name is required");
      return;
    }
    setSaving(true);
    try {
      await createFunction({ name, description, folder });
      toast.success(`Function "${name}" created`);
      onCreated();
    } catch (e) {
      toast.error("Failed to create function");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-clay-800 border-l border-clay-600 z-50 flex flex-col shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-clay-600">
        <h2 className="text-lg font-semibold text-clay-100">New Function</h2>
        <Button variant="ghost" size="sm" onClick={onClose} className="text-clay-300 hover:text-clay-100">
          Close
        </Button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
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
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this function do?"
            rows={3}
            className="w-full rounded-md bg-clay-900 border border-clay-600 text-clay-100 text-sm p-2.5 placeholder:text-clay-500 focus:outline-none focus:ring-1 focus:ring-kiln-teal"
          />
        </div>

        <div>
          <label className="text-xs font-medium text-clay-300 mb-1 block">Folder</label>
          <Input
            value={folder}
            onChange={(e) => setFolder(e.target.value)}
            placeholder="Uncategorized"
            className="bg-clay-900 border-clay-600 text-clay-100"
          />
        </div>

        <div className="pt-2 text-xs text-clay-400">
          After creating, you can add inputs, outputs, and steps from the function detail view or use the AI builder to describe what you want.
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-clay-600 flex items-center gap-2 justify-end">
        <Button variant="outline" onClick={onClose} className="border-clay-600 text-clay-300">
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          disabled={saving || !name.trim()}
          className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
        >
          {saving ? "Creating..." : "Create Function"}
        </Button>
      </div>
    </div>
  );
}
