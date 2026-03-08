"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { ClientEditor } from "@/components/context/client-editor";
import { KnowledgeEditor } from "@/components/context/knowledge-editor";
import { PromptPreview } from "@/components/context/prompt-preview";
import { FileTree } from "@/components/context/file-tree";
import { FileTabs } from "@/components/context/file-tabs";
import { Breadcrumbs } from "@/components/context/breadcrumbs";
import { FileToolbar } from "@/components/context/file-toolbar";
import { FileGrid } from "@/components/context/file-grid";
import { FilePreviewPanel } from "@/components/context/file-preview-panel";
import { StatusBar } from "@/components/context/status-bar";
import { saveFileVersion } from "@/components/context/version-history";
import { useFileExplorer } from "@/hooks/use-file-explorer";
import type { ClientProfile, KnowledgeBaseFile, FileNode } from "@/lib/types";
import {
  fetchClient,
  fetchSkillContent,
  createClient,
  updateClient,
  deleteClient as apiDeleteClient,
  updateKnowledgeFile,
  createKnowledgeFile,
  deleteKnowledgeFile,
  updateSkillContent,
  createSkillFile,
  deleteSkillFile,
} from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AnimatePresence } from "framer-motion";
import { toast } from "sonner";

export default function ContextPage() {
  const explorer = useFileExplorer();

  // Sheet editors
  const [clientEditorOpen, setClientEditorOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<ClientProfile | null>(null);
  const [clientSaving, setClientSaving] = useState(false);

  const [kbEditorOpen, setKbEditorOpen] = useState(false);
  const [editingKb, setEditingKb] = useState<KnowledgeBaseFile | null>(null);
  const [kbSaving, setKbSaving] = useState(false);

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<FileNode | null>(null);

  // Prompt preview dialog
  const [promptPreviewOpen, setPromptPreviewOpen] = useState(false);

  // ── Derive current drive ────────────────────────────────────
  const currentDriveId = (() => {
    for (const id of [...explorer.currentPath].reverse()) {
      const node = explorer.nodeMap.get(id);
      if (node?.type === "drive") return node.driveId;
      if (node) return node.driveId;
    }
    return undefined;
  })();

  // ── File content loading for preview ────────────────────────
  const [fileContent, setFileContent] = useState<string | null>(null);

  useEffect(() => {
    if (!explorer.selectedFile) {
      setFileContent(null);
      return;
    }
    const file = explorer.selectedFile;
    if (file.content !== undefined) {
      setFileContent(file.content);
      return;
    }
    // Load content for clients and skills
    if (file.driveId === "clients" && file.slug) {
      fetchClient(file.slug)
        .then((p) => setFileContent(p.raw_markdown))
        .catch(() => setFileContent("Failed to load content"));
    } else if (file.driveId === "skills" && file.slug) {
      fetchSkillContent(file.slug)
        .then((r) => setFileContent(r.content))
        .catch(() => setFileContent("Failed to load content"));
    }
  }, [explorer.selectedFile]);

  // Augmented selected file with loaded content
  const selectedFileWithContent = explorer.selectedFile
    ? { ...explorer.selectedFile, content: fileContent ?? explorer.selectedFile.content }
    : null;

  // ── CRUD handlers ───────────────────────────────────────────
  const handleNewFile = useCallback(() => {
    if (currentDriveId === "clients") {
      setEditingClient(null);
      setClientEditorOpen(true);
    } else if (currentDriveId === "knowledge-base") {
      setEditingKb(null);
      setKbEditorOpen(true);
    } else if (currentDriveId === "skills") {
      const name = prompt("Skill name (lowercase, hyphens):");
      if (!name) return;
      const template = `---\nmodel_tier: sonnet\n---\n\n# ${name}\n\nYour skill instructions here.\n`;
      createSkillFile(name.toLowerCase().replace(/\s+/g, "-"), template)
        .then(() => {
          toast.success("Skill created");
          explorer.loadAll();
        })
        .catch((e) => toast.error("Failed to create skill", { description: (e as Error).message }));
    }
  }, [currentDriveId, explorer]);

  const handleEditFile = useCallback(
    (nodeId: string) => {
      const node = explorer.nodeMap.get(nodeId);
      if (!node) return;
      if (node.driveId === "clients" && node.slug) {
        fetchClient(node.slug)
          .then((p) => {
            setEditingClient(p);
            setClientEditorOpen(true);
          })
          .catch(() => toast.error("Failed to load client"));
      } else if (node.driveId === "knowledge-base") {
        const kbFile: KnowledgeBaseFile = {
          path: (node.meta?.path as string) || "",
          category: node.category || "",
          name: node.name,
          content: node.content || "",
        };
        setEditingKb(kbFile);
        setKbEditorOpen(true);
      } else if (node.driveId === "skills") {
        // Inline edit via preview panel
        explorer.selectFile(nodeId);
        explorer.setEditMode(true);
      }
    },
    [explorer]
  );

  const handleDoubleClick = useCallback(
    (nodeId: string) => {
      const node = explorer.nodeMap.get(nodeId);
      if (!node) return;
      if (node.driveId === "skills") {
        explorer.selectFile(nodeId);
        explorer.setEditMode(true);
      } else {
        handleEditFile(nodeId);
      }
    },
    [explorer, handleEditFile]
  );

  const handleSaveClient = async (data: Parameters<typeof createClient>[0]) => {
    setClientSaving(true);
    try {
      if (editingClient) {
        await updateClient(editingClient.slug, data);
        toast.success("Client updated");
      } else {
        await createClient(data);
        toast.success("Client created");
      }
      setClientEditorOpen(false);
      setEditingClient(null);
      explorer.loadAll();
    } catch (e) {
      toast.error("Failed to save client", { description: (e as Error).message });
    } finally {
      setClientSaving(false);
    }
  };

  const handleSaveKb = async (category: string, filename: string, content: string) => {
    setKbSaving(true);
    try {
      await updateKnowledgeFile(category, filename, content);
      toast.success("Knowledge base file updated");
      setKbEditorOpen(false);
      explorer.loadAll();
    } catch (e) {
      toast.error("Failed to save file", { description: (e as Error).message });
    } finally {
      setKbSaving(false);
    }
  };

  const handleCreateKb = async (category: string, filename: string, content: string) => {
    setKbSaving(true);
    try {
      await createKnowledgeFile({ category, filename, content });
      toast.success("Knowledge base file created");
      setKbEditorOpen(false);
      explorer.loadAll();
    } catch (e) {
      toast.error("Failed to create file", { description: (e as Error).message });
    } finally {
      setKbSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      if (deleteTarget.driveId === "clients" && deleteTarget.slug) {
        await apiDeleteClient(deleteTarget.slug);
      } else if (deleteTarget.driveId === "knowledge-base") {
        const path = (deleteTarget.meta?.path as string) || "";
        const parts = path.split("/");
        await deleteKnowledgeFile(parts[0], parts[parts.length - 1]);
      } else if (deleteTarget.driveId === "skills" && deleteTarget.slug) {
        await deleteSkillFile(deleteTarget.slug);
      }
      toast.success("Deleted");
      setDeleteTarget(null);
      if (explorer.selectedFileId === deleteTarget.id) {
        explorer.selectFile(null);
        explorer.setPreviewOpen(false);
      }
      explorer.loadAll();
    } catch (e) {
      toast.error("Failed to delete", { description: (e as Error).message });
    }
  };

  const handleInlineSave = async (content: string) => {
    const file = explorer.selectedFile;
    if (!file) return;
    try {
      if (file.driveId === "knowledge-base") {
        const path = (file.meta?.path as string) || "";
        const parts = path.split("/");
        await updateKnowledgeFile(parts[0], parts[parts.length - 1], content);
      } else if (file.driveId === "skills" && file.slug) {
        await updateSkillContent(file.slug, content);
      }
      saveFileVersion(file.id, content);
      toast.success("Saved");
      explorer.setEditMode(false);
      explorer.loadAll();
    } catch (e) {
      toast.error("Failed to save", { description: (e as Error).message });
    }
  };

  const handleRename = (_nodeId: string, _newName: string) => {
    explorer.confirmRename();
    // Rename requires backend support beyond current scope — just confirm for now
  };

  const handleCopyPath = (node: FileNode) => {
    const path =
      (node.meta?.path as string) ||
      `${node.driveId}/${node.slug || node.name}`;
    navigator.clipboard.writeText(path);
    toast.success("Path copied");
  };

  // ── Keyboard shortcuts ──────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;

      if (e.key === "Backspace" || ((e.metaKey || e.ctrlKey) && e.key === "ArrowUp")) {
        e.preventDefault();
        explorer.navigateUp();
      }
      if (e.key === "Enter" && explorer.selectedFileId) {
        handleDoubleClick(explorer.selectedFileId);
      }
      if (e.key === "Delete" && explorer.selectedFile) {
        setDeleteTarget(explorer.selectedFile);
      }
      if (e.key === "F2" && explorer.selectedFileId) {
        explorer.startRename(explorer.selectedFileId);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "d" && explorer.selectedFileId) {
        e.preventDefault();
        explorer.toggleFavorite(explorer.selectedFileId);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "t") {
        e.preventDefault();
        explorer.openTab("root");
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "w") {
        e.preventDefault();
        explorer.closeTab(explorer.activeTabId);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [explorer, handleDoubleClick]);

  // ── Path string for status bar ──────────────────────────────
  const pathString = explorer.breadcrumbs.map((b) => b.name).join(" / ");

  if (explorer.loading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Context Hub" />
        <div className="flex-1 flex items-center justify-center text-clay-500 text-sm">
          Loading file explorer...
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header title="Context Hub" />

      <div className="flex flex-1 overflow-hidden">
        {/* Tree Sidebar */}
        <div className="hidden md:flex w-60 shrink-0 border-r border-clay-800 bg-clay-950 flex-col">
          <FileTree
            tree={explorer.fileTree}
            expandedFolders={explorer.expandedFolders}
            selectedFileId={explorer.selectedFileId}
            favorites={explorer.favorites}
            favoriteNodes={explorer.favoriteNodes}
            currentFolderId={explorer.currentFolderId}
            onToggleFolder={explorer.toggleFolder}
            onNavigate={(id) => {
              explorer.navigateTo(id);
              explorer.openTab(id);
            }}
            onSelectFile={(id) => explorer.selectFile(id)}
            onToggleFavorite={explorer.toggleFavorite}
          />
        </div>

        {/* Main Area */}
        <div className="flex flex-1 flex-col min-w-0">
          {/* Tabs */}
          <FileTabs
            tabs={explorer.openTabs}
            activeTabId={explorer.activeTabId}
            onSelectTab={(tabId) => {
              const tab = explorer.openTabs.find((t) => t.id === tabId);
              if (tab) {
                explorer.navigateTo(tab.nodeId);
              }
            }}
            onCloseTab={explorer.closeTab}
            onNewTab={() => explorer.openTab("root")}
          />

          {/* Breadcrumbs + Toolbar */}
          <div className="flex items-center justify-between gap-4 border-b border-clay-800/50 px-4 py-2">
            <Breadcrumbs
              items={explorer.breadcrumbs}
              onNavigate={explorer.navigateTo}
            />
            <FileToolbar
              searchQuery={explorer.searchQuery}
              onSearchChange={explorer.setSearchQuery}
              viewMode={explorer.viewMode}
              onViewModeChange={explorer.setViewMode}
              currentDriveId={currentDriveId}
              onNewFile={handleNewFile}
              onPreviewPrompt={() => setPromptPreviewOpen(true)}
            />
          </div>

          {/* Grid */}
          <div className="flex-1 overflow-auto p-4">
            <FileGrid
              items={explorer.currentFolderContents}
              viewMode={explorer.viewMode}
              selectedFileId={explorer.selectedFileId}
              renamingId={explorer.renamingId}
              selectedIds={explorer.selectedIds}
              usageMap={explorer.usageMap}
              onSelect={(id) => explorer.selectFile(id)}
              onDoubleClick={handleDoubleClick}
              onNavigate={(id) => {
                explorer.navigateTo(id);
                explorer.openTab(id);
              }}
              onRename={handleRename}
              onToggleSelect={explorer.toggleSelect}
              onContextMenu={() => {}}
            />
          </div>

          {/* Status Bar */}
          <StatusBar
            itemCount={explorer.currentFolderContents.length}
            currentPath={pathString}
            selectedCount={explorer.selectedIds.size}
            selectedFile={selectedFileWithContent}
          />
        </div>

        {/* Preview Panel */}
        <AnimatePresence>
          {explorer.previewOpen && selectedFileWithContent && (
            <FilePreviewPanel
              file={selectedFileWithContent}
              open={explorer.previewOpen}
              editMode={explorer.editMode}
              isFavorite={explorer.favorites.includes(selectedFileWithContent.id)}
              usageMap={explorer.usageMap}
              onClose={() => {
                explorer.setPreviewOpen(false);
                explorer.setEditMode(false);
              }}
              onEdit={() => {
                if (explorer.editMode) {
                  explorer.setEditMode(false);
                } else {
                  if (selectedFileWithContent.driveId === "clients") {
                    handleEditFile(selectedFileWithContent.id);
                  } else {
                    explorer.setEditMode(true);
                  }
                }
              }}
              onDelete={() => setDeleteTarget(selectedFileWithContent)}
              onToggleFavorite={() =>
                explorer.toggleFavorite(selectedFileWithContent.id)
              }
              onSave={handleInlineSave}
              onCancelEdit={() => explorer.setEditMode(false)}
            />
          )}
        </AnimatePresence>
      </div>

      {/* Client Editor Sheet */}
      <ClientEditor
        open={clientEditorOpen}
        onOpenChange={setClientEditorOpen}
        client={editingClient}
        saving={clientSaving}
        onSave={handleSaveClient}
      />

      {/* KB Editor Sheet */}
      <KnowledgeEditor
        open={kbEditorOpen}
        onOpenChange={setKbEditorOpen}
        file={editingKb}
        saving={kbSaving}
        onSave={handleSaveKb}
        onCreate={handleCreateKb}
        categories={Object.keys(explorer.kbFiles).sort()}
      />

      {/* Prompt Preview Dialog */}
      <Dialog open={promptPreviewOpen} onOpenChange={setPromptPreviewOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto border-clay-800 bg-clay-950">
          <DialogHeader>
            <DialogTitle className="text-clay-100">Prompt Preview</DialogTitle>
            <DialogDescription className="text-clay-500">
              Preview the assembled prompt with skill + context files.
            </DialogDescription>
          </DialogHeader>
          <PromptPreview clients={explorer.clients} />
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <DialogContent className="border-clay-800 bg-clay-950">
          <DialogHeader>
            <DialogTitle className="text-clay-100">Delete File</DialogTitle>
            <DialogDescription className="text-clay-500">
              Are you sure you want to delete &quot;{deleteTarget?.name}&quot;?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              className="border-clay-700 text-clay-300"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDelete}
              className="bg-kiln-coral text-white hover:bg-kiln-coral/80"
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
