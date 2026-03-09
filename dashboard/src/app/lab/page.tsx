"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PipelineList } from "@/components/pipelines/pipeline-list";
import { PipelineBuilder } from "@/components/pipelines/pipeline-builder";
import { PipelineTestPanel } from "@/components/pipelines/pipeline-test-panel";
import { VariantList } from "@/components/lab/variant-list";
import { VariantEditor } from "@/components/lab/variant-editor";
import { ExperimentList } from "@/components/lab/experiment-list";
import { ExperimentSetup } from "@/components/lab/experiment-setup";
import { ExperimentRunner } from "@/components/lab/experiment-runner";
import { ResultsComparison } from "@/components/lab/results-comparison";
import type { PipelineDefinition, PipelineStepConfig, VariantDef, Experiment } from "@/lib/types";
import {
  fetchPipelines,
  fetchSkills,
  createPipeline,
  updatePipeline,
  deletePipeline,
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

function LabInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const activeTab = searchParams.get("tab") === "lab" ? "lab" : "pipelines";

  const setActiveTab = (tab: string) => {
    const params = new URLSearchParams();
    if (tab === "lab") params.set("tab", "lab");
    router.replace(`/lab?${params.toString()}`);
  };

  // ─── Pipelines state ───
  const [pipelines, setPipelines] = useState<PipelineDefinition[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [pipelineView, setPipelineView] = useState("list");
  const [editing, setEditing] = useState<PipelineDefinition | null>(null);
  const [pipelineSaving, setPipelineSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<PipelineDefinition | null>(null);
  const [testingPipeline, setTestingPipeline] = useState<string | null>(null);

  // ─── Lab state ───
  const [selectedSkill, setSelectedSkill] = useState("");
  const [variants, setVariants] = useState<VariantDef[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingVariant, setEditingVariant] = useState<VariantDef | null>(null);
  const [labSaving, setLabSaving] = useState(false);
  const [viewingExp, setViewingExp] = useState<Experiment | null>(null);
  const [deleteVariantConfirm, setDeleteVariantConfirm] = useState<VariantDef | null>(null);
  const [deleteExpConfirm, setDeleteExpConfirm] = useState<Experiment | null>(null);

  // ─── Pipelines logic ───
  const loadPipelines = useCallback(() => {
    fetchPipelines()
      .then((res) => setPipelines(res.pipelines))
      .catch(() => toast.error("Failed to load pipelines"));
  }, []);

  useEffect(() => {
    loadPipelines();
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

  const handlePipelineSave = async (data: {
    name: string;
    description: string;
    steps: PipelineStepConfig[];
  }) => {
    setPipelineSaving(true);
    try {
      if (editing) {
        await updatePipeline(data.name, {
          description: data.description,
          steps: data.steps,
        });
        toast.success("Pipeline updated");
      } else {
        await createPipeline(data);
        toast.success("Pipeline created");
      }
      setEditing(null);
      setPipelineView("list");
      loadPipelines();
    } catch (e) {
      toast.error("Failed to save pipeline", {
        description: (e as Error).message,
      });
    } finally {
      setPipelineSaving(false);
    }
  };

  const handlePipelineDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await deletePipeline(deleteConfirm.name);
      toast.success("Pipeline deleted");
      setDeleteConfirm(null);
      loadPipelines();
    } catch (e) {
      toast.error("Failed to delete pipeline", {
        description: (e as Error).message,
      });
    }
  };

  const handlePipelineEdit = (p: PipelineDefinition) => {
    setEditing(p);
    setPipelineView("builder");
  };

  const handlePipelineNew = () => {
    setEditing(null);
    setPipelineView("builder");
  };

  // ─── Lab logic ───
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
    setLabSaving(true);
    try {
      if (editingVariant) {
        await updateVariant(selectedSkill, editingVariant.id, { label, content });
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
      setLabSaving(false);
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
    setLabSaving(true);
    try {
      await createExperiment(data);
      toast.success("Experiment created");
      loadExperiments();
    } catch (e) {
      toast.error("Failed to create", { description: (e as Error).message });
    } finally {
      setLabSaving(false);
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
    <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-clay-900 border border-clay-800 mb-6">
          <TabsTrigger
            value="pipelines"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Pipelines
          </TabsTrigger>
          <TabsTrigger
            value="lab"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Lab
          </TabsTrigger>
        </TabsList>

        {/* ─── Pipelines Tab ─── */}
        <TabsContent value="pipelines">
          <Tabs value={pipelineView} onValueChange={setPipelineView}>
            <div className="flex items-center justify-between mb-6">
              <TabsList className="bg-clay-900 border border-clay-800">
                <TabsTrigger
                  value="list"
                  className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
                >
                  My Pipelines
                </TabsTrigger>
                <TabsTrigger
                  value="builder"
                  className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
                >
                  Builder
                </TabsTrigger>
              </TabsList>
              {pipelineView === "list" && (
                <Button
                  onClick={handlePipelineNew}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
                >
                  New Pipeline
                </Button>
              )}
            </div>

            <TabsContent value="list">
              <PipelineList
                pipelines={pipelines}
                onEdit={handlePipelineEdit}
                onDelete={(p) => setDeleteConfirm(p)}
                onTest={(p) => setTestingPipeline(p.name)}
              />
            </TabsContent>

            <TabsContent value="builder">
              <PipelineBuilder
                skills={skills}
                initial={editing}
                saving={pipelineSaving}
                onSave={handlePipelineSave}
              />
            </TabsContent>
          </Tabs>
        </TabsContent>

        {/* ─── Lab Tab ─── */}
        <TabsContent value="lab">
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
                <div className="rounded-xl border border-clay-800 bg-white shadow-sm p-4">
                  <h4 className="text-sm font-medium text-clay-300 mb-4">
                    New Experiment
                  </h4>
                  <ExperimentSetup
                    skills={skills}
                    saving={labSaving}
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
              {experiments.filter((e) => Object.keys(e.results).length > 0).length === 0 ? (
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
        </TabsContent>
      </Tabs>

      {/* ─── Pipeline Dialogs ─── */}
      <Dialog
        open={deleteConfirm !== null}
        onOpenChange={(open) => !open && setDeleteConfirm(null)}
      >
        <DialogContent className="border-clay-800 bg-clay-950">
          <DialogHeader>
            <DialogTitle className="text-clay-100">Delete Pipeline</DialogTitle>
            <DialogDescription className="text-clay-500">
              Are you sure you want to delete &quot;{deleteConfirm?.name}
              &quot;? This will remove the YAML file permanently.
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
              onClick={handlePipelineDelete}
              className="bg-kiln-coral text-white hover:bg-kiln-coral/80"
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Sheet
        open={testingPipeline !== null}
        onOpenChange={(open) => !open && setTestingPipeline(null)}
      >
        <SheetContent
          side="right"
          className="w-full sm:max-w-lg bg-clay-900 border-clay-800 overflow-y-auto"
        >
          <SheetHeader>
            <SheetTitle className="text-clay-100">
              Test: {testingPipeline}
            </SheetTitle>
            <SheetDescription className="text-clay-500">
              Run the pipeline with sample data
            </SheetDescription>
          </SheetHeader>
          {testingPipeline && (
            <div className="px-4 pb-4">
              <PipelineTestPanel pipelineName={testingPipeline} />
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* ─── Lab Dialogs ─── */}
      <VariantEditor
        open={editorOpen}
        onOpenChange={setEditorOpen}
        variant={editingVariant}
        saving={labSaving}
        onSave={handleSaveVariant}
      />

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
                <SheetTitle className="text-clay-100">
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

export default function SkillsLabPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Skills Lab" />
      <Suspense>
        <LabInner />
      </Suspense>
    </div>
  );
}
