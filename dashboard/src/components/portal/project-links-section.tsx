"use client";

import { useState } from "react";
import { Plus, ExternalLink, X, Link2, FileText, Figma, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ProjectLink } from "@/lib/types";

function getLinkIcon(url: string) {
  try {
    const host = new URL(url).hostname.toLowerCase();
    if (host.includes("google.com") || host.includes("docs.google")) return FileText;
    if (host.includes("figma.com")) return Figma;
    if (host.includes("notion.so") || host.includes("notion.site")) return FileText;
    if (host.includes("loom.com")) return ExternalLink;
    return Globe;
  } catch {
    return Link2;
  }
}

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}

interface ProjectLinksSectionProps {
  links: ProjectLink[];
  onAddLink: (title: string, url: string) => void;
  onDeleteLink: (linkId: string) => void;
}

export function ProjectLinksSection({ links, onAddLink, onDeleteLink }: ProjectLinksSectionProps) {
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");

  const handleAdd = () => {
    if (!url.trim()) return;
    const linkTitle = title.trim() || getDomain(url.trim());
    onAddLink(linkTitle, url.trim());
    setTitle("");
    setUrl("");
    setAdding(false);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-clay-400">
          <Link2 className="h-3.5 w-3.5" />
          <span className="font-medium">Links</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setAdding(!adding)}
          className="h-6 text-[11px] text-clay-400 hover:text-clay-200 hover:bg-clay-700 gap-1"
        >
          <Plus className="h-3 w-3" />
        </Button>
      </div>

      {/* Link list */}
      {links.length > 0 && (
        <div className="space-y-1">
          {links.map((link) => {
            const Icon = getLinkIcon(link.url);
            return (
              <div key={link.id} className="flex items-center gap-2 group">
                <Icon className="h-3.5 w-3.5 text-clay-500 flex-shrink-0" />
                <a
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-clay-300 hover:text-kiln-teal truncate flex-1 transition-colors"
                >
                  {link.title}
                </a>
                <span className="text-[9px] text-clay-600 truncate max-w-[80px] hidden group-hover:inline">
                  {getDomain(link.url)}
                </span>
                <button
                  onClick={() => onDeleteLink(link.id)}
                  className="opacity-0 group-hover:opacity-100 text-clay-500 hover:text-red-400 transition-opacity flex-shrink-0"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {links.length === 0 && !adding && (
        <button
          onClick={() => setAdding(true)}
          className="text-[11px] text-clay-500 hover:text-clay-400 transition-colors"
        >
          Pin important links here
        </button>
      )}

      {/* Add form */}
      {adding && (
        <div className="space-y-2 p-2 rounded-lg bg-clay-900 border border-clay-700">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://..."
            className="w-full bg-clay-800 border border-clay-600 rounded-md px-2.5 py-1 text-xs text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
            autoFocus
          />
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="Label (optional)"
            className="w-full bg-clay-800 border border-clay-600 rounded-md px-2.5 py-1 text-xs text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
          />
          <div className="flex justify-end gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setAdding(false); setTitle(""); setUrl(""); }}
              className="h-6 text-[10px] text-clay-400"
            >
              Cancel
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleAdd}
              disabled={!url.trim()}
              className="h-6 text-[10px] border-clay-600 text-clay-300 hover:bg-clay-700"
            >
              Add
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
