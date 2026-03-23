"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { ArrowLeft, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PortalProject } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  on_hold: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  completed: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  archived: "bg-clay-500/15 text-clay-400 border-clay-500/30",
};

const STATUS_OPTIONS = ["active", "on_hold", "completed", "archived"] as const;

interface ProjectHeaderProps {
  project: PortalProject;
  slug: string;
  clientName: string;
  onStatusChange: (status: string) => void;
  onDelete: () => void;
}

export function ProjectHeader({ project, slug, clientName, onStatusChange, onDelete }: ProjectHeaderProps) {
  return (
    <div className="space-y-2">
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
        <div className="flex items-center gap-3">
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
    </div>
  );
}
