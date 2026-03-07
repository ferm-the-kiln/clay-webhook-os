"use client";

import { useState } from "react";
import type { PlayDefinition, PlayCategory } from "@/lib/types";
import { PlayCard } from "./play-card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Loader2, Plus } from "lucide-react";

const CATEGORIES: { value: string; label: string }[] = [
  { value: "all", label: "All" },
  { value: "outbound", label: "Outbound" },
  { value: "research", label: "Research" },
  { value: "meeting-prep", label: "Meeting Prep" },
  { value: "nurture", label: "Nurture" },
  { value: "competitive", label: "Competitive" },
  { value: "custom", label: "Custom" },
];

interface PlayGalleryProps {
  plays: PlayDefinition[];
  loading: boolean;
  onView: (play: PlayDefinition) => void;
  onFork: (play: PlayDefinition) => void;
  onDelete: (play: PlayDefinition) => void;
  onNew: () => void;
}

export function PlayGallery({
  plays,
  loading,
  onView,
  onFork,
  onDelete,
  onNew,
}: PlayGalleryProps) {
  const [category, setCategory] = useState("all");

  const filtered =
    category === "all"
      ? plays
      : plays.filter((p) => p.category === category);

  const countByCategory = (cat: string) =>
    cat === "all" ? plays.length : plays.filter((p) => p.category === cat).length;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Tabs value={category} onValueChange={setCategory}>
          <TabsList className="bg-clay-900 border border-clay-800 flex-wrap h-auto">
            {CATEGORIES.map((cat) => {
              const count = countByCategory(cat.value);
              return (
                <TabsTrigger
                  key={cat.value}
                  value={cat.value}
                  className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
                >
                  {cat.label}
                  {count > 0 && (
                    <span className="ml-1.5 text-xs text-clay-600">
                      {count}
                    </span>
                  )}
                </TabsTrigger>
              );
            })}
          </TabsList>
        </Tabs>

        <Button
          onClick={onNew}
          className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          New Play
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 text-clay-500 animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-clay-500">
          <p className="text-lg font-medium">No plays found</p>
          <p className="text-sm mt-1">
            {category === "all"
              ? "Create your first play to get started."
              : `No plays in the "${category}" category.`}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((play) => (
            <PlayCard
              key={play.name}
              play={play}
              onView={onView}
              onFork={onFork}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
