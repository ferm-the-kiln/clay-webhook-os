"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchVariants } from "@/lib/api";
import type { VariantDef } from "@/lib/types";
import { Plus, X } from "lucide-react";

export function ExperimentSetup({
  skills,
  saving,
  onSave,
}: {
  skills: string[];
  saving: boolean;
  onSave: (data: {
    skill: string;
    name: string;
    variant_ids: string[];
  }) => void;
}) {
  const [skill, setSkill] = useState("");
  const [name, setName] = useState("");
  const [variants, setVariants] = useState<VariantDef[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>(["default"]);

  useEffect(() => {
    if (!skill) {
      setVariants([]);
      return;
    }
    fetchVariants(skill)
      .then((res) => setVariants(res.variants))
      .catch(() => setVariants([]));
  }, [skill]);

  const toggleVariant = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]
    );
  };

  const handleSubmit = () => {
    if (!skill || !name || selectedIds.length < 2) return;
    onSave({ skill, name, variant_ids: selectedIds });
  };

  return (
    <div className="space-y-4 max-w-lg">
      <div>
        <label className="text-xs text-clay-500 uppercase tracking-wide mb-1.5 block">
          Skill
        </label>
        <Select value={skill} onValueChange={setSkill}>
          <SelectTrigger className="border-clay-700 bg-clay-900 text-clay-200 h-9">
            <SelectValue placeholder="Select skill..." />
          </SelectTrigger>
          <SelectContent className="border-clay-700 bg-clay-900">
            {skills.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <label className="text-xs text-clay-500 uppercase tracking-wide mb-1.5 block">
          Experiment Name
        </label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., PVC vs Direct CTA"
          className="border-clay-700 bg-clay-900 text-clay-100 placeholder:text-clay-600"
        />
      </div>

      {skill && (
        <div>
          <label className="text-xs text-clay-500 uppercase tracking-wide mb-2 block">
            Select Variants (min 2)
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => toggleVariant("default")}
              className={`px-3 py-1.5 rounded-md border text-sm transition-colors ${
                selectedIds.includes("default")
                  ? "border-kiln-teal/30 bg-kiln-teal/10 text-kiln-teal"
                  : "border-clay-700 text-clay-400 hover:border-clay-600"
              }`}
            >
              Default
            </button>
            {variants.map((v) => (
              <button
                key={v.id}
                onClick={() => toggleVariant(v.id)}
                className={`px-3 py-1.5 rounded-md border text-sm transition-colors ${
                  selectedIds.includes(v.id)
                    ? "border-kiln-teal/30 bg-kiln-teal/10 text-kiln-teal"
                    : "border-clay-700 text-clay-400 hover:border-clay-600"
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>
          {variants.length === 0 && (
            <p className="text-xs text-clay-600 mt-2">
              No variants found. Fork the skill first in the Variants tab.
            </p>
          )}
        </div>
      )}

      <Button
        onClick={handleSubmit}
        disabled={!skill || !name || selectedIds.length < 2 || saving}
        className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
      >
        {saving ? "Creating..." : "Create Experiment"}
      </Button>
    </div>
  );
}
