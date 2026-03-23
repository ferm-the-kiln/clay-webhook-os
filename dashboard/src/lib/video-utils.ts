export interface VideoEmbedInfo {
  url: string;
  provider: "youtube" | "loom" | "vimeo" | "other";
  embedUrl: string;
}

const VIDEO_PATTERNS: { pattern: RegExp; provider: VideoEmbedInfo["provider"]; getEmbedUrl: (match: RegExpMatchArray) => string }[] = [
  {
    pattern: /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)/,
    provider: "youtube",
    getEmbedUrl: (m) => `https://www.youtube.com/embed/${m[1]}`,
  },
  {
    pattern: /(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]+)/,
    provider: "youtube",
    getEmbedUrl: (m) => `https://www.youtube.com/embed/${m[1]}`,
  },
  {
    pattern: /(?:https?:\/\/)?(?:www\.)?loom\.com\/share\/([a-zA-Z0-9]+)/,
    provider: "loom",
    getEmbedUrl: (m) => `https://www.loom.com/embed/${m[1]}`,
  },
  {
    pattern: /(?:https?:\/\/)?(?:www\.)?vimeo\.com\/(\d+)/,
    provider: "vimeo",
    getEmbedUrl: (m) => `https://player.vimeo.com/video/${m[1]}`,
  },
];

export function parseVideoUrls(text: string): VideoEmbedInfo[] {
  const results: VideoEmbedInfo[] = [];
  const seen = new Set<string>();

  for (const { pattern, provider, getEmbedUrl } of VIDEO_PATTERNS) {
    const regex = new RegExp(pattern.source, "g");
    let match;
    while ((match = regex.exec(text)) !== null) {
      const embedUrl = getEmbedUrl(match);
      if (!seen.has(embedUrl)) {
        seen.add(embedUrl);
        results.push({ url: match[0], provider, embedUrl });
      }
    }
  }

  return results;
}
