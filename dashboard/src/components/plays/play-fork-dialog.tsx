"use client";

import { useState } from "react";
import type { PlayDefinition, ClientSummary } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { forkPlay } from "@/lib/api";
import { GitFork, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface PlayForkDialogProps {
  play: PlayDefinition | null;
  clients: ClientSummary[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onForked: () => void;
}

export function PlayForkDialog({
  play,
  clients,
  open,
  onOpenChange,
  onForked,
}: PlayForkDialogProps) {
  const [newName, setNewName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [clientSlug, setClientSlug] = useState<string>("none");
  const [model, setModel] = useState<string>("default");
  const [loading, setLoading] = useState(false);

  const handleOpen = (isOpen: boolean) => {
    if (isOpen && play) {
      setNewName("");
      setDisplayName("");
      setClientSlug("none");
      setModel("default");
    }
    onOpenChange(isOpen);
  };

  const handleFork = async () => {
    if (!play || !newName || !displayName) return;
    setLoading(true);
    try {
      await forkPlay(play.name, {
        new_name: newName,
        display_name: displayName,
        client_slug: clientSlug !== "none" ? clientSlug : undefined,
        default_model: model !== "default" ? model : undefined,
      });
      toast.success(`Forked as "${displayName}"`);
      onForked();
      onOpenChange(false);
    } catch (e) {
      toast.error("Fork failed", { description: (e as Error).message });
    } finally {
      setLoading(false);
    }
  };

  if (!play) return null;

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogContent className="border-clay-800 bg-clay-950">
        <DialogHeader>
          <DialogTitle className="text-clay-100 flex items-center gap-2">
            <GitFork className="h-5 w-5 text-kiln-teal" />
            Fork Play
          </DialogTitle>
          <DialogDescription className="text-clay-500">
            Create a custom version of &quot;{play.display_name}&quot;
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              Slug (URL-safe name)
            </label>
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. twelve-labs-outbound"
              className="border-clay-700 bg-clay-900 text-clay-200"
            />
          </div>

          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              Display Name
            </label>
            <Input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Twelve Labs Outbound"
              className="border-clay-700 bg-clay-900 text-clay-200"
            />
          </div>

          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              Client (optional)
            </label>
            <Select value={clientSlug} onValueChange={setClientSlug}>
              <SelectTrigger className="border-clay-700 bg-clay-900 text-clay-200">
                <SelectValue placeholder="No client" />
              </SelectTrigger>
              <SelectContent className="border-clay-700 bg-clay-900">
                <SelectItem value="none">No client</SelectItem>
                {clients.map((c) => (
                  <SelectItem key={c.slug} value={c.slug}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              Model Override
            </label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="border-clay-700 bg-clay-900 text-clay-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-clay-700 bg-clay-900">
                <SelectItem value="default">
                  Default ({play.default_model})
                </SelectItem>
                <SelectItem value="opus">Opus</SelectItem>
                <SelectItem value="sonnet">Sonnet</SelectItem>
                <SelectItem value="haiku">Haiku</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="border-clay-700 text-clay-300"
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleFork}
              disabled={loading || !newName || !displayName}
              className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
            >
              {loading && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}
              Fork Play
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
