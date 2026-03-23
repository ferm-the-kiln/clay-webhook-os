"use client";

import { ExternalLink } from "lucide-react";
import type { VideoEmbedInfo } from "@/lib/video-utils";

const PROVIDER_LABELS: Record<string, string> = {
  youtube: "YouTube",
  loom: "Loom",
  vimeo: "Vimeo",
  other: "Video",
};

interface VideoEmbedProps {
  video: VideoEmbedInfo;
}

export function VideoEmbed({ video }: VideoEmbedProps) {
  if (video.provider === "other") {
    return (
      <a
        href={video.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-xs text-kiln-teal hover:underline"
      >
        <ExternalLink className="h-3 w-3" />
        {video.url}
      </a>
    );
  }

  return (
    <div className="rounded-lg overflow-hidden border border-clay-700 bg-clay-900">
      <div className="relative w-full" style={{ paddingBottom: "56.25%" }}>
        <iframe
          src={video.embedUrl}
          title={`${PROVIDER_LABELS[video.provider]} video`}
          className="absolute inset-0 w-full h-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    </div>
  );
}
