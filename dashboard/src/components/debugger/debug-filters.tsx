"use client";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Search, X } from "lucide-react";

interface DebugFiltersProps {
  skills: string[];
  skillFilter: string;
  onSkillFilterChange: (value: string) => void;
  statusFilter: string;
  onStatusFilterChange: (value: string) => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
}

export function DebugFilters({
  skills,
  skillFilter,
  onSkillFilterChange,
  statusFilter,
  onStatusFilterChange,
  searchQuery,
  onSearchQueryChange,
}: DebugFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Skill filter */}
      <Select value={skillFilter} onValueChange={onSkillFilterChange}>
        <SelectTrigger className="w-44 border-clay-700 bg-clay-800 text-clay-200 h-9 text-sm">
          <SelectValue placeholder="All skills" />
        </SelectTrigger>
        <SelectContent className="border-clay-700 bg-clay-800">
          <SelectItem value="all">All skills</SelectItem>
          {skills.map((s) => (
            <SelectItem key={s} value={s}>
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Status filter */}
      <Select value={statusFilter} onValueChange={onStatusFilterChange}>
        <SelectTrigger className="w-36 border-clay-700 bg-clay-800 text-clay-200 h-9 text-sm">
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="border-clay-700 bg-clay-800">
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="completed">Completed</SelectItem>
          <SelectItem value="failed">Failed</SelectItem>
          <SelectItem value="processing">Processing</SelectItem>
          <SelectItem value="queued">Queued</SelectItem>
        </SelectContent>
      </Select>

      {/* Search input */}
      <div className="relative flex-1 min-w-[200px] max-w-sm">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-clay-400" />
        <Input
          placeholder="Search in data..."
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
          className="pl-8 h-9 border-clay-700 bg-clay-800 text-clay-200 text-sm placeholder:text-clay-400"
        />
        {searchQuery && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onSearchQueryChange("")}
            className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 text-clay-400 hover:text-clay-200"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    </div>
  );
}
