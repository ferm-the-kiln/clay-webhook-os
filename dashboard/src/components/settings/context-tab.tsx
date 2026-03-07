"use client";

import { useState, useEffect, useCallback } from "react";
import { ClientList } from "@/components/context/client-list";
import { ClientEditor } from "@/components/context/client-editor";
import { KnowledgeBrowser } from "@/components/context/knowledge-browser";
import { KnowledgeEditor } from "@/components/context/knowledge-editor";
import { PromptPreview } from "@/components/context/prompt-preview";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ClientProfile, ClientSummary, KnowledgeBaseFile } from "@/lib/types";
import {
  fetchClients,
  fetchClient,
  createClient,
  updateClient,
  deleteClient,
  fetchKnowledgeBase,
  updateKnowledgeFile,
  createKnowledgeFile,
  deleteKnowledgeFile,
  fetchContextUsageMap,
} from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function ContextTab() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [kbFiles, setKbFiles] = useState<Record<string, KnowledgeBaseFile[]>>(
    {}
  );

  // Client editor state
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<ClientProfile | null>(
    null
  );
  const [saving, setSaving] = useState(false);

  // KB editor state
  const [kbEditorOpen, setKbEditorOpen] = useState(false);
  const [editingKb, setEditingKb] = useState<KnowledgeBaseFile | null>(null);
  const [kbSaving, setKbSaving] = useState(false);

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<{
    slug: string;
    name: string;
  } | null>(null);

  // Usage map & KB delete
  const [usageMap, setUsageMap] = useState<Record<string, string[]>>({});
  const [kbDeleteConfirm, setKbDeleteConfirm] = useState<KnowledgeBaseFile | null>(null);

  const loadClients = useCallback(() => {
    fetchClients()
      .then((res) => setClients(res.clients))
      .catch(() => toast.error("Failed to load clients"));
  }, []);

  const loadKb = useCallback(() => {
    fetchKnowledgeBase()
      .then((res) => setKbFiles(res.knowledge_base))
      .catch(() => toast.error("Failed to load knowledge base"));
  }, []);

  const loadUsageMap = useCallback(() => {
    fetchContextUsageMap()
      .then((res) => setUsageMap(res.usage_map))
      .catch(() => {}); // silent - non-critical
  }, []);

  useEffect(() => {
    loadClients();
    loadKb();
    loadUsageMap();
  }, [loadClients, loadKb, loadUsageMap]);

  const handleAddClient = () => {
    setEditingClient(null);
    setEditorOpen(true);
  };

  const handleEditClient = async (slug: string) => {
    try {
      const profile = await fetchClient(slug);
      setEditingClient(profile);
      setEditorOpen(true);
    } catch {
      toast.error("Failed to load client");
    }
  };

  const handleSaveClient = async (data: Parameters<typeof createClient>[0]) => {
    setSaving(true);
    try {
      if (editingClient) {
        await updateClient(editingClient.slug, data);
        toast.success("Client updated");
      } else {
        await createClient(data);
        toast.success("Client created");
      }
      setEditorOpen(false);
      setEditingClient(null);
      loadClients();
    } catch (e) {
      toast.error("Failed to save client", {
        description: (e as Error).message,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClient = async () => {
    if (!deleteConfirm) return;
    try {
      await deleteClient(deleteConfirm.slug);
      toast.success("Client deleted");
      setDeleteConfirm(null);
      loadClients();
    } catch (e) {
      toast.error("Failed to delete client", {
        description: (e as Error).message,
      });
    }
  };

  const handleAddKb = () => {
    setEditingKb(null);
    setKbEditorOpen(true);
  };

  const handleCreateKb = async (category: string, filename: string, content: string) => {
    setKbSaving(true);
    try {
      await createKnowledgeFile({ category, filename, content });
      toast.success("Knowledge base file created");
      setKbEditorOpen(false);
      loadKb();
    } catch (e) {
      toast.error("Failed to create file", {
        description: (e as Error).message,
      });
    } finally {
      setKbSaving(false);
    }
  };

  const handleDeleteKb = async () => {
    if (!kbDeleteConfirm) return;
    try {
      const parts = kbDeleteConfirm.path.split("/");
      const cat = parts[0];
      const fname = parts[parts.length - 1];
      await deleteKnowledgeFile(cat, fname);
      toast.success("Knowledge base file deleted");
      setKbDeleteConfirm(null);
      loadKb();
    } catch (e) {
      toast.error("Failed to delete file", {
        description: (e as Error).message,
      });
    }
  };

  const handleSelectKb = (file: KnowledgeBaseFile) => {
    setEditingKb(file);
    setKbEditorOpen(true);
  };

  const handleSaveKb = async (
    category: string,
    filename: string,
    content: string
  ) => {
    setKbSaving(true);
    try {
      await updateKnowledgeFile(category, filename, content);
      toast.success("Knowledge base file updated");
      setKbEditorOpen(false);
      loadKb();
    } catch (e) {
      toast.error("Failed to save file", {
        description: (e as Error).message,
      });
    } finally {
      setKbSaving(false);
    }
  };

  return (
    <>
      <Tabs defaultValue="clients">
        <TabsList className="bg-clay-900 border border-clay-800 mb-6">
          <TabsTrigger
            value="clients"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Clients
          </TabsTrigger>
          <TabsTrigger
            value="knowledge"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Knowledge Base
          </TabsTrigger>
          <TabsTrigger
            value="preview"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Prompt Preview
          </TabsTrigger>
        </TabsList>

        <TabsContent value="clients">
          <ClientList
            clients={clients}
            onAdd={handleAddClient}
            onEdit={handleEditClient}
            onDelete={(slug, name) => setDeleteConfirm({ slug, name })}
          />
        </TabsContent>

        <TabsContent value="knowledge">
          <KnowledgeBrowser
            files={kbFiles}
            onSelect={handleSelectKb}
            onAdd={handleAddKb}
            onDelete={(file) => setKbDeleteConfirm(file)}
            usageMap={usageMap}
          />
        </TabsContent>

        <TabsContent value="preview">
          <PromptPreview clients={clients} />
        </TabsContent>
      </Tabs>

      {/* Client Editor Sheet */}
      <ClientEditor
        open={editorOpen}
        onOpenChange={setEditorOpen}
        client={editingClient}
        saving={saving}
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
        categories={Object.keys(kbFiles).sort()}
      />

      {/* KB Delete Confirmation Dialog */}
      <Dialog
        open={kbDeleteConfirm !== null}
        onOpenChange={(open) => !open && setKbDeleteConfirm(null)}
      >
        <DialogContent className="border-clay-800 bg-clay-950">
          <DialogHeader>
            <DialogTitle className="text-clay-100">Delete Knowledge Base File</DialogTitle>
            <DialogDescription className="text-clay-500">
              Are you sure you want to delete &quot;{kbDeleteConfirm?.name}&quot; from{" "}
              {kbDeleteConfirm?.category}? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setKbDeleteConfirm(null)}
              className="border-clay-700 text-clay-300"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteKb}
              className="bg-kiln-coral text-white hover:bg-kiln-coral/80"
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Client Confirmation Dialog */}
      <Dialog
        open={deleteConfirm !== null}
        onOpenChange={(open) => !open && setDeleteConfirm(null)}
      >
        <DialogContent className="border-clay-800 bg-clay-950">
          <DialogHeader>
            <DialogTitle className="text-clay-100">Delete Client</DialogTitle>
            <DialogDescription className="text-clay-500">
              Are you sure you want to delete &quot;{deleteConfirm?.name}
              &quot;? This will remove the client markdown file permanently.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setDeleteConfirm(null)}
              className="border-clay-700 text-clay-300"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteClient}
              className="bg-kiln-coral text-white hover:bg-kiln-coral/80"
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
