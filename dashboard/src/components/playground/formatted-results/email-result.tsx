"use client";

import { Mail } from "lucide-react";

export function EmailResult({ data }: { data: Record<string, unknown> }) {
  const subject =
    (data.subject as string) ||
    (data.subject_line as string) ||
    (data.email_subject as string) ||
    "";
  const body =
    (data.body as string) ||
    (data.email_body as string) ||
    (data.email as string) ||
    "";
  const cta =
    (data.cta as string) ||
    (data.call_to_action as string) ||
    "";

  if (!subject && !body) {
    return (
      <pre className="p-4 font-[family-name:var(--font-mono)] text-sm leading-relaxed text-clay-200">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Email header */}
      <div className="flex items-center gap-2 text-clay-500">
        <Mail className="h-4 w-4" />
        <span className="text-xs uppercase tracking-wider">Email Preview</span>
      </div>

      {/* Subject */}
      {subject && (
        <div className="rounded-lg border border-clay-800 bg-clay-900/50 p-3">
          <p className="text-xs text-clay-500 mb-1">Subject</p>
          <p className="text-sm font-medium text-clay-100">{subject}</p>
        </div>
      )}

      {/* Body */}
      {body && (
        <div className="rounded-lg border border-clay-800 bg-clay-900/50 p-4">
          <p className="text-sm text-clay-200 whitespace-pre-wrap leading-relaxed">
            {body}
          </p>
        </div>
      )}

      {/* CTA */}
      {cta && (
        <div className="rounded-md bg-kiln-teal/10 border border-kiln-teal/20 px-3 py-2">
          <p className="text-xs text-clay-500 mb-0.5">Call to Action</p>
          <p className="text-sm font-medium text-kiln-teal">{cta}</p>
        </div>
      )}

      {/* Extra fields */}
      {Object.entries(data).filter(
        ([k]) =>
          !["subject", "subject_line", "email_subject", "body", "email_body", "email", "cta", "call_to_action", "confidence_score"].includes(k)
      ).length > 0 && (
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
