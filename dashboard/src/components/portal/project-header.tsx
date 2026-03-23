"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { ArrowLeft, Trash2, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PortalProject, ProjectLink } from "@/lib/types";
import { ProjectLinksSection } from "./project-links-section";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  on_hold: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  completed: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  archived: "bg-clay-500/15 text-clay-400 border-clay-500/30",
};

const STATUS_OPTIONS = ["active", "on_hold", "completed", "archived"] as const;

function isOverdue(dateStr: string): boolean {
  return dateStr < new Date().toISOString().split("T")[0];
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

interface ProjectHeaderProps {
  project: PortalProject;
  slug: string;
  clientName: string;
  onStatusChange: (status: string) => void;
  onDelete: () => void;
  onUpdateProject: (updates: Record<string, unknown>) => void;
  onAddLink: (title: string, url: string) => void;
  onDeleteLink: (linkId: string) => void;
}

export function ProjectHeader({
  project, slug, clientName, onStatusChange, onDelete,
  onUpdateProject, onAddLink, onDeleteLink,
}: ProjectHeaderProps) {
  const [editingDate, setEditingDate] = useState(false);

  return (
    <div className="space-y-3">
      {/* Back link */}
      <Link
        href={`/clients/${slug}`}
        className="inline-flex items-center gap-1.5 text-xs text-clay-400 hover:text-clay-200 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        {clientName}
      </Link>

      {/* Title row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-wrap">
          <div
            className="h-4 w-4 rounded-full flex-shrink-0"
            style={{ backgroundColor: project.color }}
          />
          <h1 className="text-xl font-bold text-clay-50">{project.name}</h1>

          {/* Status selector */}
          <select
            value={project.status}
            onChange={(e) => onStatusChange(e.target.value)}
            className={cn(
              "text-[11px] px-2 py-0.5 rounded-full border font-medium appearance-none cursor-pointer bg-transparent",
              STATUS_COLORS[project.status] || STATUS_COLORS.active,
            )}
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s} className="bg-clay-800 text-clay-200">
                {s.replace("_", " ")}
              </option>
            ))}
          </select>

          {/* Due date */}
          {editingDate ? (
            <input
              type="date"
              defaultValue={project.due_date || ""}
              onChange={(e) => {
                onUpdateProject({ due_date: e.target.value || null });
                setEditingDate(false);
              }}
              onBlur={() => setEditingDate(false)}
              className="text-xs bg-clay-900 border border-clay-600 rounded-md px-2 py-0.5 text-clay-200 focus:outline-none focus:border-kiln-teal"
              autoFocus
            />
          ) : project.due_date ? (
            <button
              onClick={() => setEditingDate(true)}
              className={cn(
                "inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border font-medium",
                isOverdue(project.due_date)
                  ? "bg-red-500/15 text-red-400 border-red-500/30"
                  : "bg-clay-700 text-clay-400 border-clay-600",
              )}
            >
              <Calendar className="h-3 w-3" />
              Target: {formatDate(project.due_date)}
            </button>
          ) : (
            <button
              onClick={() => setEditingDate(true)}
              className="text-[11px] text-clay-500 hover:text-clay-400 transition-colors flex items-center gap-1"
            >
              <Calendar className="h-3 w-3" />
              Set target date
            </button>
          )}
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={onDelete}
          className="text-clay-500 hover:text-red-400 hover:bg-red-500/10"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Description */}
      {project.description && (
        <p className="text-sm text-clay-400 max-w-2xl">{project.description}</p>
      )}

      {/* Pinned links */}
      <ProjectLinksSection
        links={project.links ?? []}
        onAddLink={onAddLink}
        onDeleteLink={onDeleteLink}
      />
    </div>
  );
}
