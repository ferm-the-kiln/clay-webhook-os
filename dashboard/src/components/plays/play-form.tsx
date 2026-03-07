"use client";

import { useState } from "react";
import type { PlayCategory, SchemaField, PipelineDefinition } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
import { createPlay } from "@/lib/api";
import { Loader2, Plus, X } from "lucide-react";
import { toast } from "sonner";

interface PlayFormProps {
  pipelines: PipelineDefinition[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}

const CATEGORIES: { value: PlayCategory; label: string }[] = [
  { value: "outbound", label: "Outbound" },
  { value: "research", label: "Research" },
  { value: "meeting-prep", label: "Meeting Prep" },
  { value: "nurture", label: "Nurture" },
  { value: "competitive", label: "Competitive" },
  { value: "custom", label: "Custom" },
];

function emptyField(): SchemaField {
  return { name: "", type: "string", required: false, description: "", example: null };
}

export function PlayForm({
  pipelines,
  open,
  onOpenChange,
  onCreated,
}: PlayFormProps) {
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<PlayCategory>("outbound");
  const [pipeline, setPipeline] = useState("");
  const [whenToUse, setWhenToUse] = useState("");
  const [whoItsFor, setWhoItsFor] = useState("");
  const [model, setModel] = useState("opus");
  const [tags, setTags] = useState("");
  const [inputSchema, setInputSchema] = useState<SchemaField[]>([emptyField()]);
  const [outputSchema, setOutputSchema] = useState<SchemaField[]>([emptyField()]);
  const [loading, setLoading] = useState(false);

  const handleOpen = (isOpen: boolean) => {
    if (isOpen) {
      setName("");
      setDisplayName("");
      setDescription("");
      setCategory("outbound");
      setPipeline("");
      setWhenToUse("");
      setWhoItsFor("");
      setModel("opus");
      setTags("");
      setInputSchema([emptyField()]);
      setOutputSchema([emptyField()]);
    }
    onOpenChange(isOpen);
  };

  const updateField = (
    schema: SchemaField[],
    setSchema: (s: SchemaField[]) => void,
    index: number,
    key: keyof SchemaField,
    value: string | boolean
  ) => {
    const updated = [...schema];
    updated[index] = { ...updated[index], [key]: value };
    setSchema(updated);
  };

  const addField = (
    schema: SchemaField[],
    setSchema: (s: SchemaField[]) => void
  ) => {
    setSchema([...schema, emptyField()]);
  };

  const removeField = (
    schema: SchemaField[],
    setSchema: (s: SchemaField[]) => void,
    index: number
  ) => {
    setSchema(schema.filter((_, i) => i !== index));
  };

  const handleCreate = async () => {
    if (!name || !displayName || !pipeline) return;
    setLoading(true);
    try {
      const cleanSchema = (fields: SchemaField[]) =>
        fields.filter((f) => f.name.trim() !== "");
      await createPlay({
        name,
        display_name: displayName,
        description,
        category,
        pipeline,
        input_schema: cleanSchema(inputSchema),
        output_schema: cleanSchema(outputSchema),
        when_to_use: whenToUse,
        who_its_for: whoItsFor,
        default_model: model,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      toast.success(`Play "${displayName}" created`);
      onCreated();
      handleOpen(false);
    } catch (e) {
      toast.error("Failed to create play", {
        description: (e as Error).message,
      });
    } finally {
      setLoading(false);
    }
  };

  const renderSchemaBuilder = (
    label: string,
    schema: SchemaField[],
    setSchema: (s: SchemaField[]) => void
  ) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs text-clay-500">{label}</label>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => addField(schema, setSchema)}
          className="h-6 px-2 text-clay-500 hover:text-clay-200"
        >
          <Plus className="h-3 w-3 mr-1" />
          Add
        </Button>
      </div>
      {schema.map((field, i) => (
        <div key={i} className="flex items-center gap-2">
          <Input
            placeholder="field_name"
            value={field.name}
            onChange={(e) => updateField(schema, setSchema, i, "name", e.target.value)}
            className="border-clay-700 bg-clay-900 text-clay-200 text-xs flex-1"
          />
          <Select
            value={field.type}
            onValueChange={(v) => updateField(schema, setSchema, i, "type", v)}
          >
            <SelectTrigger className="border-clay-700 bg-clay-900 text-clay-200 text-xs w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-clay-700 bg-clay-900">
              <SelectItem value="string">string</SelectItem>
              <SelectItem value="number">number</SelectItem>
              <SelectItem value="boolean">boolean</SelectItem>
            </SelectContent>
          </Select>
          <Input
            placeholder="description"
            value={field.description}
            onChange={(e) => updateField(schema, setSchema, i, "description", e.target.value)}
            className="border-clay-700 bg-clay-900 text-clay-200 text-xs flex-1"
          />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => removeField(schema, setSchema, i)}
            className="h-8 w-8 p-0 text-clay-600 hover:text-kiln-coral shrink-0"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogContent className="border-clay-800 bg-clay-950 max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-clay-100">New Play</DialogTitle>
          <DialogDescription className="text-clay-500">
            Create a new GTM play with input/output schemas
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-clay-500 mb-1 block">Slug</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="cold-outbound"
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
                placeholder="Cold Outbound"
                className="border-clay-700 bg-clay-900 text-clay-200"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              Description
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this play does..."
              className="border-clay-700 bg-clay-900 text-clay-200 min-h-[60px]"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-clay-500 mb-1 block">
                Category
              </label>
              <Select value={category} onValueChange={(v) => setCategory(v as PlayCategory)}>
                <SelectTrigger className="border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c.value} value={c.value}>
                      {c.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-clay-500 mb-1 block">
                Pipeline
              </label>
              <Select value={pipeline} onValueChange={setPipeline}>
                <SelectTrigger className="border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue placeholder="Select..." />
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
              <label className="text-xs text-clay-500 mb-1 block">Model</label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger className="border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  <SelectItem value="opus">Opus</SelectItem>
                  <SelectItem value="sonnet">Sonnet</SelectItem>
                  <SelectItem value="haiku">Haiku</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              When to Use
            </label>
            <Textarea
              value={whenToUse}
              onChange={(e) => setWhenToUse(e.target.value)}
              placeholder="When should someone use this play?"
              className="border-clay-700 bg-clay-900 text-clay-200 min-h-[48px]"
            />
          </div>

          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              Who It&apos;s For
            </label>
            <Textarea
              value={whoItsFor}
              onChange={(e) => setWhoItsFor(e.target.value)}
              placeholder="Who is the target user?"
              className="border-clay-700 bg-clay-900 text-clay-200 min-h-[48px]"
            />
          </div>

          <div>
            <label className="text-xs text-clay-500 mb-1 block">
              Tags (comma-separated)
            </label>
            <Input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="outbound, email, high-volume"
              className="border-clay-700 bg-clay-900 text-clay-200"
            />
          </div>

          {renderSchemaBuilder("Input Schema", inputSchema, setInputSchema)}
          {renderSchemaBuilder("Output Schema", outputSchema, setOutputSchema)}

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              onClick={() => handleOpen(false)}
              className="border-clay-700 text-clay-300"
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={loading || !name || !displayName || !pipeline}
              className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
            >
              {loading && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}
              Create Play
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
