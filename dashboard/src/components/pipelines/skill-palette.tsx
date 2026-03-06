"use client";

import { useDraggable } from "@dnd-kit/core";
import { Badge } from "@/components/ui/badge";
import { GripVertical } from "lucide-react";

function DraggableSkill({ skill }: { skill: string }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `palette-${skill}`,
    data: { skill, fromPalette: true },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`flex items-center gap-1.5 cursor-grab active:cursor-grabbing ${
        isDragging ? "opacity-50" : ""
      }`}
    >
      <Badge
        variant="outline"
        className="bg-clay-800 text-clay-200 border-clay-700 hover:bg-clay-700 hover:border-clay-600 transition-colors py-1.5 px-3 text-sm"
      >
        <GripVertical className="h-3 w-3 mr-1 text-clay-500" />
        {skill}
      </Badge>
    </div>
  );
}

export function SkillPalette({ skills }: { skills: string[] }) {
  return (
    <div className="rounded-xl border border-clay-800 bg-clay-900 p-4">
      <p className="text-xs text-clay-500 uppercase tracking-wide mb-3">
        Drag skills to build pipeline
      </p>
      <div className="flex flex-wrap gap-2">
        {skills.map((s) => (
          <DraggableSkill key={s} skill={s} />
        ))}
      </div>
    </div>
  );
}
