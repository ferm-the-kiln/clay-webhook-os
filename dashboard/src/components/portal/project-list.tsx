"use client";

import { useState } from "react";
import { Plus, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ProjectSummary } from "@/lib/types";
import { ProjectCard } from "./project-card";
import { CreateProjectDialog } from "./create-project-dialog";

interface ProjectListProps {
  slug: string;
  projects: ProjectSummary[];
  onProjectCreated: () => void;
}

export function ProjectList({ slug, projects, onProjectCreated }: ProjectListProps) {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-clay-400">
          <FolderOpen className="h-3.5 w-3.5" />
          <span className="font-medium">Projects</span>
          {projects.length > 0 && (
            <span className="text-clay-500">({projects.length})</span>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setDialogOpen(true)}
          className="h-7 text-xs text-clay-400 hover:text-clay-200 hover:bg-clay-700 gap-1"
        >
          <Plus className="h-3 w-3" />
          New
        </Button>
      </div>

      {projects.length === 0 ? (
        <button
          onClick={() => setDialogOpen(true)}
          className="w-full rounded-lg border border-dashed border-clay-600 py-4 text-xs text-clay-500 hover:border-clay-500 hover:text-clay-400 transition-colors"
        >
          Create a project to organize your work
        </button>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-thin scrollbar-thumb-clay-600">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} slug={slug} />
          ))}
        </div>
      )}

      <CreateProjectDialog
        slug={slug}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCreated={() => {
          setDialogOpen(false);
          onProjectCreated();
        }}
      />
    </div>
  );
}
