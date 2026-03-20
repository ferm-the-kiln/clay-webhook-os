"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Textarea } from "@/components/ui/textarea";
import { ChevronDown } from "lucide-react";

const TONE_LABELS = ["Very Formal", "Formal", "Professional", "Conversational", "Casual"];
const LENGTH_OPTIONS = [
  { value: "short", label: "Short", desc: "50-80 words" },
  { value: "medium", label: "Medium", desc: "80-125 words" },
  { value: "long", label: "Long", desc: "125-175 words" },
];
const OPENING_STYLES = [
  { value: "question", label: "Question", desc: "Open with a thought-provoking question" },
  { value: "statement", label: "Statement", desc: "Lead with a bold claim or observation" },
  { value: "stat", label: "Stat/Data", desc: "Open with a compelling statistic" },
  { value: "story", label: "Story", desc: "Open with a brief anecdote or scenario" },
];

function buildInstructionText(config: {
  tone: number;
  length: string;
  opening: string;
  urgency: boolean;
  customNote: string;
}): string {
  const parts: string[] = [];

  // Tone
  const toneMap: Record<number, string> = {
    0: "Use a very formal, executive-level tone. Polished and professional.",
    1: "Use a formal tone. Professional but not stiff.",
    2: "Use a professional tone. Warm but business-appropriate.",
    3: "Use a conversational tone. Friendly and approachable.",
    4: "Use a casual, peer-to-peer tone. No corporate speak.",
  };
  if (config.tone !== 2) {
    parts.push(toneMap[config.tone]);
  }

  // Length
  const lengthMap: Record<string, string> = {
    short: "Keep under 80 words. Be concise and punchy.",
    long: "Aim for 125-175 words. Include more detail and context.",
  };
  if (config.length !== "medium" && lengthMap[config.length]) {
    parts.push(lengthMap[config.length]);
  }

  // Opening
  const openingMap: Record<string, string> = {
    question: "Open with a thought-provoking question related to their signal.",
    statement: "Open with a bold statement or observation about their business.",
    stat: "Open with a compelling statistic or data point relevant to their industry.",
    story: "Open with a brief scenario or anecdote that resonates with their situation.",
  };
  if (openingMap[config.opening]) {
    parts.push(openingMap[config.opening]);
  }

  // Urgency
  if (config.urgency) {
    parts.push("Add a time-sensitive element or urgency to the CTA.");
  }

  // Custom note
  if (config.customNote.trim()) {
    parts.push(config.customNote.trim());
  }

  return parts.join("\n");
}

export function InstructionBuilder({
  instructions,
  onInstructionsChange,
}: {
  instructions: string;
  onInstructionsChange: (v: string) => void;
}) {
  const [tone, setTone] = useState(2); // Professional default
  const [length, setLength] = useState("medium");
  const [opening, setOpening] = useState("");
  const [urgency, setUrgency] = useState(false);
  const [customNote, setCustomNote] = useState("");
  const [showRaw, setShowRaw] = useState(false);

  // Sync generated text → instructions whenever builder changes
  useEffect(() => {
    const text = buildInstructionText({ tone, length, opening, urgency, customNote });
    onInstructionsChange(text);
  }, [tone, length, opening, urgency, customNote, onInstructionsChange]);

  return (
    <div className="flex flex-col h-full gap-3 overflow-y-auto">
      {/* Tone slider */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-clay-300">Tone</label>
        <input
          type="range"
          min={0}
          max={4}
          value={tone}
          onChange={(e) => setTone(Number(e.target.value))}
          className="w-full accent-kiln-teal h-1.5"
        />
        <div className="flex justify-between text-[10px] text-clay-300">
          <span>Formal</span>
          <span className="text-kiln-teal font-medium">{TONE_LABELS[tone]}</span>
          <span>Casual</span>
        </div>
      </div>

      {/* Length selector */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-clay-300">Length</label>
        <div className="flex gap-1">
          {LENGTH_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setLength(opt.value)}
              className={cn(
                "flex-1 text-center py-1.5 rounded-md text-xs transition-colors",
                length === opt.value
                  ? "bg-kiln-teal/15 text-kiln-teal border border-kiln-teal/30"
                  : "text-clay-300 hover:text-clay-200 hover:bg-clay-700/50 border border-transparent"
              )}
            >
              <span className="font-medium">{opt.label}</span>
              <span className="block text-[9px] text-clay-300 mt-0.5">
                {opt.desc}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Opening style */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-clay-300">
          Opening Style
        </label>
        <div className="grid grid-cols-2 gap-1">
          {OPENING_STYLES.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setOpening(opening === opt.value ? "" : opt.value)}
              className={cn(
                "text-left px-2.5 py-2 rounded-md text-xs transition-colors border",
                opening === opt.value
                  ? "bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30"
                  : "text-clay-300 hover:text-clay-200 hover:bg-clay-700/50 border-transparent"
              )}
            >
              <span className="font-medium block">{opt.label}</span>
              <span className="text-[9px] text-clay-300 block mt-0.5 leading-tight">
                {opt.desc}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Urgency toggle */}
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-clay-300">Add Urgency</label>
        <button
          onClick={() => setUrgency(!urgency)}
          className={cn(
            "relative w-9 h-5 rounded-full transition-colors",
            urgency ? "bg-kiln-teal" : "bg-clay-600"
          )}
        >
          <span
            className={cn(
              "absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform",
              urgency ? "translate-x-4" : "translate-x-0.5"
            )}
          />
        </button>
      </div>

      {/* Custom note */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-clay-300">
          Custom Note
        </label>
        <Textarea
          value={customNote}
          onChange={(e) => setCustomNote(e.target.value)}
          placeholder='e.g. "mention we met at SaaStr" or "focus on the funding signal"'
          rows={2}
          className="bg-clay-950 text-xs resize-none leading-relaxed"
        />
      </div>

      {/* Show raw instructions */}
      <button
        onClick={() => setShowRaw(!showRaw)}
        className="flex items-center gap-1 text-[10px] text-clay-300 hover:text-clay-300 transition-colors"
      >
        <ChevronDown
          className={cn(
            "h-3 w-3 transition-transform",
            showRaw && "rotate-180"
          )}
        />
        {showRaw ? "Hide" : "Show"} generated instructions
      </button>
      {showRaw && (
        <Textarea
          value={instructions}
          onChange={(e) => onInstructionsChange(e.target.value)}
          rows={4}
          className="bg-clay-950 text-[11px] font-[family-name:var(--font-mono)] resize-none leading-relaxed"
        />
      )}
    </div>
  );
}
