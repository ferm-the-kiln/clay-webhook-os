"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { DestinationForm } from "@/components/destinations/destination-form";
import { DestinationList } from "@/components/destinations/destination-list";
import type { Destination, DestinationType } from "@/lib/types";
import {
  fetchDestinations,
  createDestination,
  updateDestination,
  deleteDestination,
  testDestination,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Plus } from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Destination | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Destination | null>(null);

  const load = useCallback(() => {
    fetchDestinations()
      .then((res) => setDestinations(res.destinations))
      .catch(() => toast.error("Failed to load destinations"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (data: {
    name: string;
    type: DestinationType;
    url: string;
    auth_header_name: string;
    auth_header_value: string;
    client_slug: string | null;
  }) => {
    setSaving(true);
    try {
      await createDestination(data);
      toast.success("Destination created");
      setDialogOpen(false);
      load();
    } catch (e) {
      toast.error("Failed to create destination", {
        description: (e as Error).message,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async (data: {
    name: string;
    type: DestinationType;
    url: string;
    auth_header_name: string;
    auth_header_value: string;
    client_slug: string | null;
  }) => {
    if (!editing) return;
    setSaving(true);
    try {
      await updateDestination(editing.id, data);
      toast.success("Destination updated");
      setEditing(null);
      setDialogOpen(false);
      load();
    } catch (e) {
      toast.error("Failed to update destination", {
        description: (e as Error).message,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await deleteDestination(deleteConfirm.id);
      toast.success("Destination deleted");
      setDeleteConfirm(null);
      load();
    } catch (e) {
      toast.error("Failed to delete destination", {
        description: (e as Error).message,
      });
    }
  };

  const handleTest = async (dest: Destination) => {
    setTestingId(dest.id);
    try {
      const result = await testDestination(dest.id);
      if (result.ok) {
        toast.success("Connection successful", {
          description: `${dest.name} responded with status ${result.status_code}`,
        });
      } else {
        toast.error("Connection failed", {
          description: result.error || `Status ${result.status_code}`,
        });
      }
    } catch (e) {
      toast.error("Test failed", { description: (e as Error).message });
    } finally {
      setTestingId(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Settings" />
      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-clay-100">Destinations</h3>
            <p className="text-sm text-clay-500">
              Push batch results to Clay tables or webhook endpoints.
            </p>
          </div>
          <Button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
            className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Destination
          </Button>
        </div>

        <DestinationList
          destinations={destinations}
          onEdit={(dest) => {
            setEditing(dest);
            setDialogOpen(true);
          }}
          onDelete={(dest) => setDeleteConfirm(dest)}
          onTest={handleTest}
          testingId={testingId}
        />

        {/* Create / Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="border-clay-800 bg-clay-950">
            <DialogHeader>
              <DialogTitle className="text-clay-100">
                {editing ? "Edit Destination" : "New Destination"}
              </DialogTitle>
              <DialogDescription className="text-clay-500">
                {editing
                  ? "Update the destination configuration."
                  : "Configure where to push batch results."}
              </DialogDescription>
            </DialogHeader>
            <DestinationForm
              initial={editing}
              onSubmit={editing ? handleUpdate : handleCreate}
              loading={saving}
            />
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog
          open={deleteConfirm !== null}
          onOpenChange={(open) => !open && setDeleteConfirm(null)}
        >
          <DialogContent className="border-clay-800 bg-clay-950">
            <DialogHeader>
              <DialogTitle className="text-clay-100">Delete Destination</DialogTitle>
              <DialogDescription className="text-clay-500">
                Are you sure you want to delete &quot;{deleteConfirm?.name}&quot;? This
                action cannot be undone.
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
                onClick={handleDelete}
                className="bg-kiln-coral text-white hover:bg-kiln-coral/80"
              >
                Delete
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
