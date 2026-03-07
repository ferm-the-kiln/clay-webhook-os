"use client";

import type { PlayDefinition, PlayCategory } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowRight, GitFork, Trash2, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

const CATEGORY_COLORS: Record<PlayCategory, string> = {
  outbound: "bg-teal-500/10 text-teal-400 border-teal-500/30",
  research: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  "meeting-prep": "bg-purple-500/10 text-purple-400 border-purple-500/30",
  nurture: "bg-green-500/10 text-green-400 border-green-500/30",
  competitive: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  custom: "bg-clay-500/10 text-clay-400 border-clay-500/30",
};

interface PlayCardProps {
  play: PlayDefinition;
  onView: (play: PlayDefinition) => void;
  onFork: (play: PlayDefinition) => void;
  onDelete: (play: PlayDefinition) => void;
}

export function PlayCard({ play, onView, onFork, onDelete }: PlayCardProps) {
  const skills = play.pipeline ? play.pipeline.split(",").map((s) => s.trim()) : [];

  return (
    <Card
      className="border-clay-800 bg-clay-950 hover:border-clay-700 transition-colors cursor-pointer group"
      onClick={() => onView(play)}
    >
      <CardContent className="p-5 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1 min-w-0">
            <h3 className="font-semibold text-clay-100 truncate">
              {play.display_name}
            </h3>
            <p className="text-sm text-clay-400 line-clamp-2">
              {play.description}
            </p>
          </div>
          <ChevronRight className="h-4 w-4 text-clay-600 group-hover:text-clay-400 shrink-0 mt-1 transition-colors" />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Badge
            variant="outline"
            className={cn("text-xs", CATEGORY_COLORS[play.category])}
          >
            {play.category}
          </Badge>
          {play.forked_from && (
            <Badge
              variant="outline"
              className="text-xs bg-clay-800/50 text-clay-500 border-clay-700"
            >
              <GitFork className="h-3 w-3 mr-1" />
              {play.forked_from}
            </Badge>
          )}
          {play.tags.slice(0, 2).map((tag) => (
            <Badge
              key={tag}
              variant="outline"
              className="text-xs bg-clay-900 text-clay-500 border-clay-800"
            >
              {tag}
            </Badge>
          ))}
        </div>

        <div className="flex items-center gap-1.5 text-xs text-clay-500">
          <span className="font-mono">{play.pipeline}</span>
          <ArrowRight className="h-3 w-3" />
          <span>{play.input_schema.length} inputs</span>
          <ArrowRight className="h-3 w-3" />
          <span>{play.output_schema.length} outputs</span>
        </div>

        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-clay-600">
            model: {play.default_model}
          </span>
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onFork(play)}
              className="h-7 px-2 text-clay-500 hover:text-clay-200"
            >
              <GitFork className="h-3.5 w-3.5" />
            </Button>
            {!play.is_template && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete(play)}
                className="h-7 px-2 text-clay-500 hover:text-kiln-coral"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export { CATEGORY_COLORS };
