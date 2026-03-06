"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Papa from "papaparse";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  fetchPipelines,
  fetchDestinations,
  fetchClients,
  createCampaign,
  addCampaignAudience,
} from "@/lib/api";
import type {
  PipelineDefinition,
  Destination,
  ClientSummary,
  Campaign,
} from "@/lib/types";
import { Upload, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface CreateCampaignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (campaign: Campaign) => void;
}

export function CreateCampaignDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateCampaignDialogProps) {
  const [pipelines, setPipelines] = useState<PipelineDefinition[]>([]);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [saving, setSaving] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [pipeline, setPipeline] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [clientSlug, setClientSlug] = useState("");
  const [goalDescription, setGoalDescription] = useState("");
  const [targetCount, setTargetCount] = useState(100);
  const [metric, setMetric] = useState("emails_sent");
  const [frequency, setFrequency] = useState("manual");
  const [batchSize, setBatchSize] = useState(25);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.8);
  const [model, setModel] = useState("opus");
  const [instructions, setInstructions] = useState("");
  const [audienceRows, setAudienceRows] = useState<Record<string, unknown>[]>(
    []
  );
  const [audienceFileName, setAudienceFileName] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDropdowns = useCallback(() => {
    fetchPipelines()
      .then((res) => setPipelines(res.pipelines))
      .catch(() => {});
    fetchDestinations()
      .then((res) => setDestinations(res.destinations))
      .catch(() => {});
    fetchClients()
      .then((res) => setClients(res.clients))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (open) loadDropdowns();
  }, [open, loadDropdowns]);

  const resetForm = () => {
    setName("");
    setDescription("");
    setPipeline("");
    setDestinationId("");
    setClientSlug("");
    setGoalDescription("");
    setTargetCount(100);
    setMetric("emails_sent");
    setFrequency("manual");
    setBatchSize(25);
    setConfidenceThreshold(0.8);
    setModel("opus");
    setInstructions("");
    setAudienceRows([]);
    setAudienceFileName("");
  };

  const handleFileUpload = (file: File) => {
    Papa.parse<Record<string, string>>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        if (result.data.length > 0) {
          setAudienceRows(result.data);
          setAudienceFileName(file.name);
          toast.success("Audience loaded", {
            description: `${result.data.length} rows from ${file.name}`,
          });
        }
      },
      error: () => {
        toast.error("Failed to parse CSV");
      },
    });
  };

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast.error("Campaign name is required");
      return;
    }
    if (!pipeline) {
      toast.error("Pipeline is required");
      return;
    }

    setSaving(true);
    try {
      const campaign = await createCampaign({
        name: name.trim(),
        description: description.trim() || undefined,
        pipeline,
        destination_id: destinationId || null,
        client_slug: clientSlug || null,
        goal: {
          description: goalDescription.trim() || undefined,
          target_count: targetCount,
          metric,
        },
        schedule: {
          frequency,
          batch_size: batchSize,
        },
        confidence_threshold: confidenceThreshold,
        instructions: instructions.trim() || undefined,
        model,
      });

      // Upload audience if provided
      if (audienceRows.length > 0) {
        try {
          await addCampaignAudience(campaign.id, audienceRows);
          toast.success("Campaign created with audience", {
            description: `${audienceRows.length} rows uploaded`,
          });
        } catch {
          toast.warning("Campaign created, but audience upload failed", {
            description: "You can add audience later from the campaign detail.",
          });
        }
      } else {
        toast.success("Campaign created");
      }

      onCreated(campaign);
      resetForm();
      onOpenChange(false);
    } catch (e) {
      toast.error("Failed to create campaign", {
        description: (e as Error).message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-clay-800 bg-clay-950 max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-clay-100 font-[family-name:var(--font-sans)]">
            New Campaign
          </DialogTitle>
          <DialogDescription className="text-clay-500">
            Set up an automated campaign with a pipeline, audience, and delivery
            schedule.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          {/* Name + Description */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
                Name *
              </label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Q2 Outbound Campaign"
                className="border-clay-700 bg-clay-900 text-clay-200 placeholder:text-clay-600"
              />
            </div>
            <div>
              <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
                Model
              </label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  <SelectItem value="opus">Opus (highest quality)</SelectItem>
                  <SelectItem value="sonnet">Sonnet (balanced)</SelectItem>
                  <SelectItem value="haiku">Haiku (fast)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
              Description
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the campaign purpose..."
              rows={2}
              className="border-clay-700 bg-clay-900 text-clay-200 placeholder:text-clay-600 min-h-0"
            />
          </div>

          {/* Pipeline + Destination + Client */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
                Pipeline *
              </label>
              <Select value={pipeline} onValueChange={setPipeline}>
                <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue placeholder="Select pipeline..." />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  {pipelines.map((p) => (
                    <SelectItem key={p.name} value={p.name}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
                Destination
              </label>
              <Select
                value={destinationId || "none"}
                onValueChange={(v) =>
                  setDestinationId(v === "none" ? "" : v)
                }
              >
                <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  <SelectItem value="none">None</SelectItem>
                  {destinations.map((d) => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
                Client
              </label>
              <Select
                value={clientSlug || "none"}
                onValueChange={(v) =>
                  setClientSlug(v === "none" ? "" : v)
                }
              >
                <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  <SelectItem value="none">None</SelectItem>
                  {clients.map((c) => (
                    <SelectItem key={c.slug} value={c.slug}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Goal */}
          <div>
            <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
              Goal
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Input
                type="number"
                min={1}
                value={targetCount}
                onChange={(e) => setTargetCount(Number(e.target.value))}
                placeholder="100"
                className="border-clay-700 bg-clay-900 text-clay-200 placeholder:text-clay-600"
              />
              <Select value={metric} onValueChange={setMetric}>
                <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  <SelectItem value="emails_sent">emails sent</SelectItem>
                  <SelectItem value="leads_qualified">
                    leads qualified
                  </SelectItem>
                  <SelectItem value="meetings_booked">
                    meetings booked
                  </SelectItem>
                  <SelectItem value="rows_processed">
                    rows processed
                  </SelectItem>
                </SelectContent>
              </Select>
              <Input
                value={goalDescription}
                onChange={(e) => setGoalDescription(e.target.value)}
                placeholder="Goal description (optional)"
                className="border-clay-700 bg-clay-900 text-clay-200 placeholder:text-clay-600"
              />
            </div>
          </div>

          {/* Schedule */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
                Frequency
              </label>
              <Select value={frequency} onValueChange={setFrequency}>
                <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  <SelectItem value="manual">Manual</SelectItem>
                  <SelectItem value="hourly">Hourly</SelectItem>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
                Batch Size
              </label>
              <Input
                type="number"
                min={1}
                max={500}
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
                className="border-clay-700 bg-clay-900 text-clay-200"
              />
            </div>
          </div>

          {/* Confidence Threshold */}
          <div>
            <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
              Confidence Threshold:{" "}
              <span className="text-kiln-teal">
                {(confidenceThreshold * 100).toFixed(0)}%
              </span>
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={confidenceThreshold * 100}
              onChange={(e) =>
                setConfidenceThreshold(Number(e.target.value) / 100)
              }
              className="w-full h-2 rounded-full appearance-none cursor-pointer bg-clay-800 accent-kiln-teal"
            />
            <div className="flex justify-between text-[10px] text-clay-600 mt-1">
              <span>0% (review all)</span>
              <span>100% (auto-send all)</span>
            </div>
          </div>

          {/* Instructions */}
          <div>
            <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
              Custom Instructions
            </label>
            <Textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Optional instructions for the AI model..."
              rows={2}
              className="border-clay-700 bg-clay-900 text-clay-200 placeholder:text-clay-600 min-h-0"
            />
          </div>

          {/* Audience CSV Upload */}
          <div>
            <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
              Audience (CSV)
            </label>
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                e.currentTarget.classList.add("border-kiln-teal");
              }}
              onDragLeave={(e) => {
                e.currentTarget.classList.remove("border-kiln-teal");
              }}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove("border-kiln-teal");
                const file = e.dataTransfer.files[0];
                if (file) handleFileUpload(file);
              }}
              className="cursor-pointer border-2 border-dashed border-clay-700 rounded-lg bg-clay-900/50 hover:border-kiln-teal/50 transition-all duration-200 p-4 text-center"
            >
              <Upload className="h-5 w-5 text-clay-600 mx-auto mb-1" />
              {audienceFileName ? (
                <p className="text-sm text-kiln-teal">
                  {audienceFileName} ({audienceRows.length} rows)
                </p>
              ) : (
                <p className="text-xs text-clay-500">
                  Drop a CSV or click to upload audience rows
                </p>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileUpload(file);
                }}
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <Button
            variant="outline"
            onClick={() => {
              resetForm();
              onOpenChange(false);
            }}
            className="border-clay-700 text-clay-300"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={saving || !name.trim() || !pipeline}
            className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
          >
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Create Campaign
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
