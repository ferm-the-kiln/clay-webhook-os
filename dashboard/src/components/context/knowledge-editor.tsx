"use client";

import { useState, useEffect, useMemo } from "react";
import type { KnowledgeBaseFile } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";

interface KnowledgeEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  file: KnowledgeBaseFile | null;
  saving: boolean;
  onSave: (category: string, filename: string, content: string) => void;
  onCreate: (category: string, filename: string, content: string) => void;
  categories: string[];
}

function slugify(val: string): string {
  return val
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function KnowledgeEditor({
  open,
  onOpenChange,
  file,
  saving,
  onSave,
  onCreate,
  categories,
}: KnowledgeEditorProps) {
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("");
  const [customCategory, setCustomCategory] = useState("");
  const [filename, setFilename] = useState("");
  const isCreate = !file;

  useEffect(() => {
    if (file) {
      setContent(file.content);
      setCategory(file.category);
      setFilename(file.path.split("/").pop() || file.path);
    } else {
      setContent("");
      setCategory(categories[0] || "");
      setCustomCategory("");
      setFilename("");
    }
  }, [file, open, categories]);

  const stats = useMemo(() => {
    const words = content.trim() ? content.trim().split(/\s+/).length : 0;
    const tokens = Math.ceil(content.length / 4);
    return { words, tokens };
  }, [content]);

  const resolvedCategory =
    category === "__new__" ? slugify(customCategory) : category;

  const canSubmit =
    resolvedCategory.length > 0 &&
    (isCreate ? filename.trim().length > 0 : true) &&
    content.trim().length > 0;

  const handleSubmit = () => {
    const finalFilename = isCreate
      ? filename.trim().endsWith(".md")
        ? filename.trim()
        : `${filename.trim()}.md`
      : file!.path.split("/").pop() || file!.path;
    if (isCreate) {
      onCreate(resolvedCategory, finalFilename, content);
    } else {
      onSave(file!.category, finalFilename, content);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl bg-clay-950 border-clay-800 flex flex-col"
      >
        <SheetHeader className="px-6 pt-6 pb-2">
          <SheetTitle className="text-clay-100">
            {isCreate ? "New Knowledge Base File" : file!.name}
          </SheetTitle>
          <SheetDescription className="text-clay-500">
            {isCreate ? (
              "Create a new knowledge base file"
            ) : (
              <span className="flex items-center gap-2">
                <Badge
                  variant="secondary"
                  className="bg-clay-800 text-clay-300 border-clay-700 text-xs"
                >
                  {file!.category}
                </Badge>
                <span className="font-mono text-xs">{file!.path}</span>
              </span>
            )}
          </SheetDescription>
        </SheetHeader>

        {isCreate && (
          <div className="px-6 space-y-3 pb-3">
            <div>
              <label className="text-xs font-medium text-clay-400 mb-1.5 block">
                Category
              </label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="bg-clay-900 border-clay-700 text-clay-100">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent className="bg-clay-900 border-clay-700">
                  {categories.map((cat) => (
                    <SelectItem key={cat} value={cat} className="text-clay-100">
                      {cat}
                    </SelectItem>
                  ))}
                  <SelectItem value="__new__" className="text-kiln-teal">
                    + New category...
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            {category === "__new__" && (
              <div>
                <label className="text-xs font-medium text-clay-400 mb-1.5 block">
                  New Category Name
                </label>
                <Input
                  placeholder="e.g. templates"
                  value={customCategory}
                  onChange={(e) => setCustomCategory(e.target.value)}
                  className="bg-clay-900 border-clay-700 text-clay-100 placeholder:text-clay-600"
                />
                {customCategory && (
                  <p className="text-xs text-clay-500 mt-1">
                    Will be created as: <span className="font-mono text-clay-400">{slugify(customCategory)}/</span>
                  </p>
                )}
              </div>
            )}
            <div>
              <label className="text-xs font-medium text-clay-400 mb-1.5 block">
                Filename
              </label>
              <Input
                placeholder="e.g. my-framework"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                className="bg-clay-900 border-clay-700 text-clay-100 placeholder:text-clay-600"
              />
              {filename && !filename.endsWith(".md") && (
                <p className="text-xs text-clay-500 mt-1">
                  Will be saved as: <span className="font-mono text-clay-400">{filename.trim()}.md</span>
                </p>
              )}
            </div>
          </div>
        )}

        <div className="flex-1 px-6 pb-2 min-h-0">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={isCreate ? "# Title\n\nWrite your knowledge base content here..." : undefined}
            className="w-full h-full min-h-[300px] rounded-md bg-clay-900 border border-clay-700 text-clay-100 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-kiln-teal/50 resize-none"
          />
        </div>
        <div className="px-6 pb-2">
          <p className="text-xs text-clay-500 text-right">
            {stats.words} words · ~{stats.tokens} tokens
          </p>
        </div>
        <div className="px-6 pb-6">
          <Button
            onClick={handleSubmit}
            disabled={saving || !canSubmit}
            className="w-full bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
          >
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {isCreate ? "Create File" : "Save Changes"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
