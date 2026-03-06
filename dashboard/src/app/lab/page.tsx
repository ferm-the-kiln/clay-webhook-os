"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VariantList } from "@/components/lab/variant-list";
import { VariantEditor } from "@/components/lab/variant-editor";
import { ExperimentList } from "@/components/lab/experiment-list";
import { ExperimentSetup } from "@/components/lab/experiment-setup";
import { ExperimentRunner } from "@/components/lab/experiment-runner";
import { ResultsComparison } from "@/components/lab/results-comparison";
import type { VariantDef, Experiment } from "@/lib/types";
import {
  fetchSkills,
  fetchVariants,
  forkVariant,
  createVariant,
  updateVariant,
  deleteVariant,
  fetchExperiments,
  createExperiment,
  deleteExperiment,
  getExperiment,
} from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function LabPage() {
  const [skills, setSkills] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState("");
  const [variants, setVariants] = useState<VariantDef[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);

  // Variant editor
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingVariant, setEditingVariant] = useState<VariantDef | null>(null);
  const [saving, setSaving] = useState(false);

  // Experiment detail
  const [viewingExp, setViewingExp] = useState<Experiment | null>(null);

  // Delete confirmations
  const [deleteVariantConfirm, setDeleteVariantConfirm] =
    useState<VariantDef | null>(null);
  const [deleteExpConfirm, setDeleteExpConfirm] = useState<Experiment | null>(
    null
  );

  useEffect(() => {
    fetchSkills()
      .then((res) => {
        setSkills(res.skills);
        if (res.skills.length > 0 && !selectedSkill) {
          setSelectedSkill(res.skills[0]);
        }
      })
      .catch(() => {});
    loadExperiments();
  }, []);

  const loadVariants = useCallback(() => {
    if (!selectedSkill) return;
    fetchVariants(selectedSkill)
      .then((res) => setVariants(res.variants))
      .catch(() => toast.error("Failed to load variants"));
  }, [selectedSkill]);

  useEffect(() => {
    loadVariants();
  }, [loadVariants]);

  const loadExperiments = () => {
    fetchExperiments()
      .then((res) => setExperiments(res.experiments))
      .catch(() => {});
  };

  const handleFork = async () => {
    try {
      await forkVariant(selectedSkill);
      toast.success("Variant forked from default");
      loadVariants();
    } catch (e) {
      toast.error("Fork failed", { description: (e as Error).message });
    }
  };

  const handleSaveVariant = async (label: string, content: string) => {
    setSaving(true);
    try {
      if (editingVariant) {
        await updateVariant(selectedSkill, editingVariant.id, {
          label,
          content,
        });
        toast.success("Variant updated");
      } else {
        await createVariant(selectedSkill, { label, content });
        toast.success("Variant created");
      }
      setEditorOpen(false);
      setEditingVariant(null);
      loadVariants();
    } catch (e) {
      toast.error("Save failed", { description: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteVariant = async () => {
    if (!deleteVariantConfirm) return;
    try {
      await deleteVariant(selectedSkill, deleteVariantConfirm.id);
      toast.success("Variant deleted");
      setDeleteVariantConfirm(null);
      loadVariants();
    } catch (e) {
      toast.error("Delete failed", { description: (e as Error).message });
    }
  };

  const handleCreateExperiment = async (data: {
    skill: string;
    name: string;
    variant_ids: string[];
  }) => {
    setSaving(true);
    try {
      await createExperiment(data);
      toast.success("Experiment created");
      loadExperiments();
    } catch (e) {
      toast.error("Failed to create", { description: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteExperiment = async () => {
    if (!deleteExpConfirm) return;
    try {
      await deleteExperiment(deleteExpConfirm.id);
      toast.success("Experiment deleted");
      setDeleteExpConfirm(null);
      loadExperiments();
    } catch (e) {
      toast.error("Delete failed", { description: (e as Error).message });
    }
  };

  const handleViewExperiment = async (exp: Experiment) => {
    try {
      const full = await getExperiment(exp.id);
      setViewingExp(full);
    } catch {
      setViewingExp(exp);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Skills Lab" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        <Tabs defaultValue="variants">
          <TabsList className="bg-clay-900 border border-clay-800 mb-6">
            <TabsTrigger
              value="variants"
              className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
            >
              Variants
            </TabsTrigger>
            <TabsTrigger
              value="experiments"
              className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
            >
              Experiments
            </TabsTrigger>
            <TabsTrigger
              value="results"
              className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
            >
              Results
            </TabsTrigger>
          </TabsList>

          <TabsContent value="variants">
            <div className="space-y-4">
              <Select value={selectedSkill} onValueChange={setSelectedSkill}>
                <SelectTrigger className="w-56 border-clay-700 bg-clay-900 text-clay-200 h-9 text-sm">
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

              {selectedSkill && (
                <VariantList
                  skill={selectedSkill}
                  variants={variants}
                  onEdit={(v) => {
                    setEditingVariant(v);
                    setEditorOpen(true);
                  }}
                  onDelete={(v) => setDeleteVariantConfirm(v)}
                  onFork={handleFork}
                />
              )}
            </div>
          </TabsContent>

          <TabsContent value="experiments">
            <div className="space-y-6">
              <div className="rounded-xl border border-clay-800 bg-clay-900 p-4">
                <h4 className="text-sm font-medium text-clay-300 mb-4">
                  New Experiment
                </h4>
                <ExperimentSetup
                  skills={skills}
                  saving={saving}
                  onSave={handleCreateExperiment}
                />
              </div>
              <ExperimentList
                experiments={experiments}
                onView={handleViewExperiment}
                onDelete={(e) => setDeleteExpConfirm(e)}
              />
            </div>
          </TabsContent>

          <TabsContent value="results">
            {experiments.filter((e) => Object.keys(e.results).length > 0)
              .length === 0 ? (
              <div className="text-center py-12">
                <p className="text-sm text-clay-500">
                  No experiment results yet. Run an experiment first.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {experiments
                  .filter((e) => Object.keys(e.results).length > 0)
                  .map((exp) => (
                    <ResultsComparison
                      key={exp.id}
                      experiment={exp}
                      onPromoted={loadExperiments}
                    />
                  ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      {/* Variant Editor Sheet */}
      <VariantEditor
        open={editorOpen}
        onOpenChange={setEditorOpen}
        variant={editingVariant}
        saving={saving}
        onSave={handleSaveVariant}
      />

      {/* Experiment Detail Sheet */}
      <Sheet
        open={viewingExp !== null}
        onOpenChange={(open) => !open && setViewingExp(null)}
      >
        <SheetContent
          side="right"
          className="w-full sm:max-w-lg bg-clay-900 border-clay-800 overflow-y-auto"
        >
          {viewingExp && (
            <>
              <SheetHeader>
                <SheetTitle className="text-kiln-cream">
                  {viewingExp.name}
                </SheetTitle>
                <SheetDescription className="text-clay-500">
                  {viewingExp.skill} — {viewingExp.status}
                </SheetDescription>
              </SheetHeader>
              <div className="px-4 pb-4 space-y-6">
                {viewingExp.status === "draft" && (
                  <ExperimentRunner
                    experiment={viewingExp}
                    onRan={() => {
                      loadExperiments();
                      handleViewExperiment(viewingExp);
                    }}
                  />
                )}
                <ResultsComparison
                  experiment={viewingExp}
                  onPromoted={loadExperiments}
                />
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Delete Variant Dialog */}
      <Dialog
        open={deleteVariantConfirm !== null}
        onOpenChange={(open) => !open && setDeleteVariantConfirm(null)}
      >
        <DialogContent className="border-clay-800 bg-clay-950">
          <DialogHeader>
            <DialogTitle className="text-clay-100">Delete Variant</DialogTitle>
            <DialogDescription className="text-clay-500">
              Delete &quot;{deleteVariantConfirm?.label}&quot;? This cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setDeleteVariantConfirm(null)}
              className="border-clay-700 text-clay-300"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteVariant}
              className="bg-kiln-coral text-white hover:bg-kiln-coral/80"
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Experiment Dialog */}
      <Dialog
        open={deleteExpConfirm !== null}
        onOpenChange={(open) => !open && setDeleteExpConfirm(null)}
      >
        <DialogContent className="border-clay-800 bg-clay-950">
          <DialogHeader>
            <DialogTitle className="text-clay-100">
              Delete Experiment
            </DialogTitle>
            <DialogDescription className="text-clay-500">
              Delete &quot;{deleteExpConfirm?.name}&quot;? Results will be lost.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setDeleteExpConfirm(null)}
              className="border-clay-700 text-clay-300"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteExperiment}
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
