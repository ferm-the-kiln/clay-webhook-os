"use client";

import { useState } from "react";
import type { KnowledgeBaseFile } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FileText, Plus, Search, Trash2 } from "lucide-react";

const CATEGORY_COLORS: Record<string, string> = {
  frameworks: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  voice: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  industries: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

interface KnowledgeBrowserProps {
  files: Record<string, KnowledgeBaseFile[]>;
  onSelect: (file: KnowledgeBaseFile) => void;
  onAdd: () => void;
  onDelete: (file: KnowledgeBaseFile) => void;
  usageMap: Record<string, string[]>;
}

export function KnowledgeBrowser({
  files,
  onSelect,
  onAdd,
  onDelete,
  usageMap,
}: KnowledgeBrowserProps) {
  const [search, setSearch] = useState("");

  const allFiles = Object.values(files).flat();
  const filtered = search
    ? allFiles.filter(
        (f) =>
          f.name.toLowerCase().includes(search.toLowerCase()) ||
          f.path.toLowerCase().includes(search.toLowerCase())
      )
    : null;

  // Group filtered files back by category
  const displayFiles: Record<string, KnowledgeBaseFile[]> = {};
  if (filtered) {
    for (const f of filtered) {
      (displayFiles[f.category] ??= []).push(f);
    }
  }

  const source = filtered ? displayFiles : files;
  const categories = Object.keys(source).sort();
  const totalFiles = allFiles.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-clay-500" />
          <Input
            placeholder="Search knowledge base..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-clay-900 border-clay-700 text-clay-100 placeholder:text-clay-600"
          />
        </div>
        <Button
          onClick={onAdd}
          className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add File
        </Button>
      </div>

      {categories.length === 0 ? (
        <div className="text-center py-12 text-clay-500">
          {totalFiles === 0
            ? "No knowledge base files yet. Add one to get started."
            : "No files match your search."}
        </div>
      ) : (
        <div className="space-y-6">
          {categories.map((category) => (
            <div key={category}>
              <h3 className="text-sm font-semibold text-clay-300 capitalize mb-3">
                {category}
              </h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {source[category].map((file) => {
                  const usedBy =
                    usageMap[`knowledge_base/${file.path}`] || [];
                  return (
                    <Card
                      key={file.path}
                      className="bg-clay-900 border-clay-800 p-4 hover:border-clay-700 transition-colors cursor-pointer"
                      onClick={() => onSelect(file)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3 min-w-0">
                          <FileText className="h-5 w-5 text-clay-500 shrink-0 mt-0.5" />
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-clay-100 truncate">
                              {file.name}
                            </p>
                            <p className="text-xs text-clay-500 font-mono mt-0.5">
                              {file.path}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDelete(file);
                          }}
                          className="text-clay-400 hover:text-kiln-coral shrink-0 ml-2"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        <Badge
                          variant="secondary"
                          className={`text-xs ${
                            CATEGORY_COLORS[category] ||
                            "bg-clay-800 text-clay-300 border-clay-700"
                          }`}
                        >
                          {category}
                        </Badge>
                        {usedBy.map((skill) => (
                          <Badge
                            key={skill}
                            variant="secondary"
                            className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/20 text-xs"
                          >
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
