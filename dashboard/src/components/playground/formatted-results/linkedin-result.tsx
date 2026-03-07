"use client";

import { Linkedin } from "lucide-react";

export function LinkedInResult({ data }: { data: Record<string, unknown> }) {
  const note =
    (data.note as string) ||
    (data.message as string) ||
    (data.linkedin_note as string) ||
    (data.connection_note as string) ||
    "";

  if (!note) {
    return (
      <pre className="p-4 font-[family-name:var(--font-mono)] text-sm leading-relaxed text-clay-200">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  }

  const charCount = note.length;
  const limit = 300;
  const isOverLimit = charCount > limit;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 text-clay-500">
        <Linkedin className="h-4 w-4" />
        <span className="text-xs uppercase tracking-wider">
          LinkedIn Connection Note
        </span>
      </div>

      {/* LinkedIn card mockup */}
      <div className="rounded-xl border border-clay-800 bg-clay-900/50 overflow-hidden">
        {/* Card header */}
        <div className="flex items-center gap-3 p-4 border-b border-clay-800">
          <div className="h-10 w-10 rounded-full bg-clay-700 flex items-center justify-center">
            <span className="text-sm font-medium text-clay-300">
              {(data.first_name as string)?.charAt(0) || "?"}
            </span>
          </div>
          <div>
            <p className="text-sm font-medium text-clay-200">
              {(data.first_name as string) || "Contact"}
              {data.last_name ? ` ${data.last_name}` : ""}
            </p>
            <p className="text-xs text-clay-500">Connection request</p>
          </div>
        </div>

        {/* Note body */}
        <div className="p-4">
          <p className="text-sm text-clay-200 whitespace-pre-wrap leading-relaxed">
            {note}
          </p>
        </div>

        {/* Character count */}
        <div className="flex items-center justify-end px-4 pb-3">
          <span
            className={`text-xs font-[family-name:var(--font-mono)] ${
              isOverLimit ? "text-kiln-coral" : "text-clay-500"
            }`}
          >
            {charCount}/{limit} characters
          </span>
        </div>
      </div>

      {/* Full JSON fallback */}
      {Object.keys(data).length > 3 && (
        <details className="group">
          <summary className="text-xs text-clay-500 cursor-pointer hover:text-clay-400">
            Show all fields
          </summary>
          <pre className="mt-2 text-xs text-clay-400 font-[family-name:var(--font-mono)] overflow-x-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
