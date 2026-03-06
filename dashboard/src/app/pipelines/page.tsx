"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PipelineList } from "@/components/pipelines/pipeline-list";
import { PipelineBuilder } from "@/components/pipelines/pipeline-builder";
import { PipelineTestPanel } from "@/components/pipelines/pipeline-test-panel";
import type { PipelineDefinition, PipelineStepConfig } from "@/lib/types";
import {
  fetchPipelines,
  fetchSkills,
  createPipeline,
  updatePipeline,
  deletePipeline,
} from "@/lib/api";
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

export default function PipelinesPage() {
  const [pipelines, setPipelines] = useState<PipelineDefinition[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [tab, setTab] = useState("list");
  const [editing, setEditing] = useState<PipelineDefinition | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<PipelineDefinition | null>(
    null
  );
  const [testingPipeline, setTestingPipeline] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchPipelines()
      .then((res) => setPipelines(res.pipelines))
      .catch(() => toast.error("Failed to load pipelines"));
  }, []);

  useEffect(() => {
    load();
    fetchSkills()
      .then((res) => setSkills(res.skills))
      .catch(() => {});
  }, [load]);

  const handleSave = async (data: {
    name: string;
    description: string;
    steps: PipelineStepConfig[];
  }) => {
    setSaving(true);
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
      setTab("list");
      load();
    } catch (e) {
      toast.error("Failed to save pipeline", {
        description: (e as Error).message,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await deletePipeline(deleteConfirm.name);
      toast.success("Pipeline deleted");
      setDeleteConfirm(null);
      load();
    } catch (e) {
      toast.error("Failed to delete pipeline", {
        description: (e as Error).message,
      });
    }
  };

  const handleEdit = (p: PipelineDefinition) => {
    setEditing(p);
    setTab("builder");
  };

  const handleNew = () => {
    setEditing(null);
    setTab("builder");
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Pipelines" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        <Tabs value={tab} onValueChange={setTab}>
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
            {tab === "list" && (
              <Button
                onClick={handleNew}
                className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
              >
                New Pipeline
              </Button>
            )}
          </div>

          <TabsContent value="list">
            <PipelineList
              pipelines={pipelines}
              onEdit={handleEdit}
              onDelete={(p) => setDeleteConfirm(p)}
              onTest={(p) => setTestingPipeline(p.name)}
            />
          </TabsContent>

          <TabsContent value="builder">
            <PipelineBuilder
              skills={skills}
              initial={editing}
              saving={saving}
              onSave={handleSave}
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* Delete Confirmation */}
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
              onClick={handleDelete}
              className="bg-kiln-coral text-white hover:bg-kiln-coral/80"
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Test Panel Sheet */}
      <Sheet
        open={testingPipeline !== null}
        onOpenChange={(open) => !open && setTestingPipeline(null)}
      >
        <SheetContent
          side="right"
          className="w-full sm:max-w-lg bg-clay-900 border-clay-800 overflow-y-auto"
        >
          <SheetHeader>
            <SheetTitle className="text-kiln-cream">
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
    </div>
  );
}
