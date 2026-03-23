"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { MessageSquare, Paperclip, CheckCircle2, Calendar } from "lucide-react";
import type { ProjectSummary } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  on_hold: "On Hold",
  completed: "Done",
  archived: "Archived",
};

function timeAgo(ts: number | null): string {
  if (!ts) return "No activity";
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(ts * 1000).toLocaleDateString();
}

export function ProjectCard({ project, slug }: { project: ProjectSummary; slug: string }) {
  const totalItems = project.update_count + project.action_count;
  const completedPhases = project.phases.filter((p) => p.status === "completed").length;
  const totalPhases = project.phases.length;

  return (
    <Link
      href={`/clients/${slug}/projects/${project.id}`}
      className="group flex-shrink-0 w-56 rounded-xl border border-clay-600 bg-clay-800 p-4 transition-all hover:border-clay-500 hover:bg-clay-750"
    >
      {/* Color bar + name */}
      <div className="flex items-center gap-2.5 mb-2">
        <div
          className="h-3 w-3 rounded-full flex-shrink-0"
          style={{ backgroundColor: project.color }}
        />
        <h4 className="text-sm font-semibold text-clay-100 truncate group-hover:text-kiln-teal transition-colors">
          {project.name}
        </h4>
      </div>

      {/* Phase progress */}
      {totalPhases > 0 && (
        <div className="mb-2.5">
          <div className="flex gap-1 mb-1">
            {project.phases
              .sort((a, b) => a.order - b.order)
              .map((ph) => (
                <div
                  key={ph.id}
                  className={cn(
                    "h-1.5 flex-1 rounded-full",
                    ph.status === "completed"
                      ? "bg-emerald-500"
                      : ph.status === "active"
                        ? "bg-kiln-teal"
                        : "bg-clay-600"
                  )}
                />
              ))}
          </div>
          <p className="text-[10px] text-clay-400">
            {project.current_phase_name
              ? project.current_phase_name
              : completedPhases === totalPhases
                ? "All phases complete"
                : `${completedPhases}/${totalPhases} phases`}
          </p>
        </div>
      )}

      {/* Stats row */}
      <div className="flex items-center gap-3 text-[11px] text-clay-400">
        {project.update_count > 0 && (
          <span className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            {project.update_count}
          </span>
        )}
        {project.media_count > 0 && (
          <span className="flex items-center gap-1">
            <Paperclip className="h-3 w-3" />
            {project.media_count}
          </span>
        )}
        {project.action_count > 0 && (
          <span className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            {project.action_count}
          </span>
        )}
        {totalItems === 0 && <span>New</span>}
      </div>

      {/* Due date or last activity */}
      <p className="text-[10px] text-clay-500 mt-1.5 flex items-center gap-1">
        {project.due_date ? (
          <>
            <Calendar className="h-2.5 w-2.5" />
            {new Date(project.due_date + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </>
        ) : (
          timeAgo(project.last_activity)
        )}
      </p>
    </Link>
  );
}
