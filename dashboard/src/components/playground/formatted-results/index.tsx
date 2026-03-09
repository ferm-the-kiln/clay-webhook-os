"use client";

import type { WebhookResponse } from "@/lib/types";
import { EmailResult } from "./email-result";
import { LinkedInResult } from "./linkedin-result";
import { BriefResult } from "./brief-result";

const FORMATTERS: Record<
  string,
  React.ComponentType<{ data: Record<string, unknown> }>
> = {
  "email-gen": EmailResult,
  "follow-up": EmailResult,
  "sequence-writer": EmailResult,
  "linkedin-note": LinkedInResult,
  "meeting-prep": BriefResult,
  "campaign-brief": BriefResult,
  "discovery-questions": BriefResult,
};

export function FormattedResult({
  skill,
  data,
}: {
  skill: string;
  data: Record<string, unknown>;
}) {
  const Formatter = FORMATTERS[skill];

  if (Formatter) {
    return <Formatter data={data} />;
  }

  // Default: pretty JSON
  return (
    <pre className="p-4 font-[family-name:var(--font-mono)] text-sm leading-relaxed text-clay-200">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
