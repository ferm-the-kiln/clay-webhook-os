"use client";

import { useState } from "react";
import { Paperclip, Image, Film, FileIcon, Download, Trash2, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PortalMedia } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";

function isImage(mime: string) {
  return mime.startsWith("image/");
}

function isVideo(mime: string) {
  return mime.startsWith("video/");
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

interface ProjectMediaSectionProps {
  slug: string;
  media: PortalMedia[];
  onDelete: (mediaId: string) => void;
}

export function ProjectMediaSection({ slug, media, onDelete }: ProjectMediaSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const COLLAPSE_THRESHOLD = 4;
  const visibleMedia = expanded ? media : media.slice(0, COLLAPSE_THRESHOLD);

  return (
    <div className="rounded-xl border border-clay-600 bg-clay-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium text-clay-300 uppercase tracking-wider flex items-center gap-1.5">
          <Paperclip className="h-3 w-3" />
          Files & Media
        </h3>
        <span className="text-[10px] text-clay-500">{media.length}</span>
      </div>

      {media.length === 0 ? (
        <p className="text-xs text-clay-500">No files yet</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            {visibleMedia.map((m) => {
              const fullUrl = m.url ? `${API_URL}${m.url}` : "";
              return (
                <div
                  key={m.id}
                  className="group rounded-lg border border-clay-700 bg-clay-900 overflow-hidden"
                >
                  {isImage(m.mime_type) && fullUrl ? (
                    <button
                      onClick={() => setPreviewUrl(fullUrl)}
                      className="w-full aspect-square bg-clay-900 flex items-center justify-center overflow-hidden"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={fullUrl}
                        alt={m.original_name}
                        className="w-full h-full object-cover"
                      />
                    </button>
                  ) : isVideo(m.mime_type) ? (
                    <div className="w-full aspect-square bg-clay-900 flex items-center justify-center">
                      <Film className="h-6 w-6 text-clay-500" />
                    </div>
                  ) : (
                    <div className="w-full aspect-square bg-clay-900 flex flex-col items-center justify-center p-2">
                      <FileIcon className="h-5 w-5 text-clay-500 mb-1" />
                      <span className="text-[9px] text-clay-500 text-center truncate w-full">
                        {m.original_name}
                      </span>
                    </div>
                  )}

                  {/* Footer */}
                  <div className="px-2 py-1.5 flex items-center justify-between">
                    <span className="text-[9px] text-clay-500 truncate flex-1">
                      {formatBytes(m.size_bytes)}
                    </span>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {fullUrl && (
                        <a
                          href={fullUrl}
                          download={m.original_name}
                          className="text-clay-500 hover:text-clay-300"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Download className="h-3 w-3" />
                        </a>
                      )}
                      <button
                        onClick={() => onDelete(m.id)}
                        className="text-clay-500 hover:text-red-400"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {media.length > COLLAPSE_THRESHOLD && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 mt-2 text-[10px] text-clay-400 hover:text-clay-200 transition-colors"
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-3 w-3" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3" />
                  {media.length - COLLAPSE_THRESHOLD} more
                </>
              )}
            </button>
          )}
        </>
      )}

      {/* Lightbox */}
      {previewUrl && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-8"
          onClick={() => setPreviewUrl(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="Preview"
            className="max-w-full max-h-full rounded-lg object-contain"
          />
        </div>
      )}
    </div>
  );
}
