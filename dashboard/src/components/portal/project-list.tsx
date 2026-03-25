"use client";

import { useState } from "react";
import { Plus, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import Link from "next/link";
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

  // Hide entirely when no projects
  if (projects.length === 0) {
    return (
      <CreateProjectDialog
        slug={slug}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCreated={() => {
          setDialogOpen(false);
          onProjectCreated();
        }}
      />
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-clay-400">
          <FolderOpen className="h-3.5 w-3.5" />
          <span className="font-medium">Projects</span>
          <span className="text-clay-500">({projects.length})</span>
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

      {/* Single project — compact inline row */}
      {projects.length === 1 ? (
        <Link
          href={`/clients/${slug}/projects/${projects[0].id}`}
          className="flex items-center gap-2.5 rounded-lg border border-clay-700/50 bg-clay-800/60 px-3 py-2.5 hover:bg-clay-800 transition-colors"
        >
          <span
            className="h-2.5 w-2.5 rounded-full shrink-0"
            style={{ backgroundColor: projects[0].color }}
          />
          <span className="text-sm font-medium text-clay-200 truncate">{projects[0].name}</span>
          {projects[0].phases.length > 0 && (
            <span className="text-[11px] text-clay-500 ml-auto shrink-0">
              {projects[0].phases.filter((p) => p.status === "completed").length}/{projects[0].phases.length} phases
            </span>
          )}
        </Link>
      ) : (
        /* Multiple projects — horizontal scroll cards */
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
