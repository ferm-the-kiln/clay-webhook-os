"use client";

import { FileText, ChevronDown } from "lucide-react";
import { useState } from "react";

function Section({
  title,
  content,
  defaultOpen = false,
}: {
  title: string;
  content: string | string[] | Record<string, unknown> | unknown;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const renderContent = () => {
    if (typeof content === "string") {
      return (
        <p className="text-sm text-clay-200 whitespace-pre-wrap leading-relaxed">
          {content}
        </p>
      );
    }
    if (Array.isArray(content)) {
      return (
        <ul className="space-y-1">
          {content.map((item, i) => (
            <li key={i} className="text-sm text-clay-200 flex items-start gap-2">
              <span className="text-kiln-teal mt-1.5 text-[8px]">{"\u25CF"}</span>
              <span>{typeof item === "string" ? item : JSON.stringify(item)}</span>
            </li>
          ))}
        </ul>
      );
    }
    return (
      <pre className="text-xs text-clay-400 font-[family-name:var(--font-mono)] overflow-x-auto">
        {JSON.stringify(content, null, 2)}
      </pre>
    );
  };

  return (
    <div className="border border-clay-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-3 hover:bg-clay-900/50 transition-colors"
      >
        <span className="text-sm font-medium text-clay-200 capitalize">
          {title.replace(/_/g, " ")}
        </span>
        <ChevronDown
          className={`h-4 w-4 text-clay-500 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open && <div className="px-3 pb-3">{renderContent()}</div>}
    </div>
  );
}

export function BriefResult({ data }: { data: Record<string, unknown> }) {
  // Extract known meeting prep / brief fields
  const knownKeys = [
    "company_overview",
    "key_talking_points",
    "talking_points",
    "questions_to_ask",
    "questions",
    "agenda",
    "meeting_agenda",
    "research",
    "company_research",
    "preparation_notes",
    "notes",
    "action_items",
    "objectives",
    "risks",
    "competitive_context",
  ];

  const sections = Object.entries(data).filter(
    ([k]) => k !== "confidence_score" && k !== "_meta"
  );

  if (sections.length === 0) {
    return (
      <pre className="p-4 font-[family-name:var(--font-mono)] text-sm leading-relaxed text-clay-200">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center gap-2 text-clay-500">
        <FileText className="h-4 w-4" />
        <span className="text-xs uppercase tracking-wider">Meeting Brief</span>
      </div>

      <div className="space-y-2">
        {sections.map(([key, value], i) => (
          <Section
            key={key}
            title={key}
            content={value as string}
            defaultOpen={i < 3}
          />
        ))}
      </div>
    </div>
  );
}
