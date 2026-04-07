"use client";

import { useState } from "react";
import { Trash2, X, FileIcon, Film, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PortalMedia } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

interface MediaGridProps {
  media: PortalMedia[];
  onDelete: (mediaId: string) => void;
}

export function MediaGrid({ media, onDelete }: MediaGridProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  if (media.length === 0) {
    return (
      <div className="text-center py-8 text-clay-400">
        <p className="text-sm">No media files yet. Upload images, screenshots, or files.</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {media.map((m) => {
          const fullUrl = m.url ? `${API_URL}${m.url}` : "";
          const driveUrl = m.drive_file_id
            ? `https://drive.google.com/file/d/${m.drive_file_id}/view`
            : null;
          const downloadUrl = driveUrl || fullUrl;
          return (
            <div
              key={m.id}
              className="group rounded-lg border border-clay-700 bg-clay-800 overflow-hidden"
            >
              {isImage(m.mime_type) && fullUrl ? (
                <button
                  onClick={() => setPreviewUrl(fullUrl)}
                  className="w-full aspect-video bg-clay-900 flex items-center justify-center overflow-hidden"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={fullUrl}
                    alt={m.caption || m.original_name}
                    className="w-full h-full object-cover"
                  />
                </button>
              ) : isVideo(m.mime_type) ? (
                <div className="w-full aspect-video bg-clay-900 flex items-center justify-center">
                  <Film className="h-8 w-8 text-clay-500" />
                </div>
              ) : (
                <div className="w-full aspect-video bg-clay-900 flex items-center justify-center">
                  <FileIcon className="h-8 w-8 text-clay-500" />
                </div>
              )}
              <div className="p-2">
                <p className="text-xs text-clay-200 truncate">{m.caption || m.original_name}</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[10px] text-clay-500">{formatBytes(m.size_bytes)}</span>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {downloadUrl && (
                      <a
                        href={downloadUrl}
                        target={driveUrl ? "_blank" : undefined}
                        rel={driveUrl ? "noopener noreferrer" : undefined}
                        download={driveUrl ? undefined : m.original_name}
                        className="text-clay-400 hover:text-clay-200"
                        title={driveUrl ? "Open in Google Drive" : "Download"}
                      >
                        <Download className="h-3.5 w-3.5" />
                      </a>
                    )}
                    <button
                      onClick={() => onDelete(m.id)}
                      className="text-clay-400 hover:text-red-400"
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Lightbox */}
      {previewUrl && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-8"
          onClick={() => setPreviewUrl(null)}
        >
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setPreviewUrl(null)}
            className="absolute top-4 right-4 text-white hover:bg-white/10"
          >
            <X className="h-6 w-6" />
          </Button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="Preview"
            className="max-w-full max-h-full rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
}
