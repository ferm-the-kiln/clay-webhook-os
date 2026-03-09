"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Mail, Linkedin, Phone, Copy, Check, ChevronDown } from "lucide-react";

const CHANNEL_CONFIG: Record<string, { icon: typeof Mail; color: string; badgeColor: string }> = {
  email: {
    icon: Mail,
    color: "text-blue-400",
    badgeColor: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  },
  linkedin: {
    icon: Linkedin,
    color: "text-purple-400",
    badgeColor: "bg-purple-500/15 text-purple-400 border-purple-500/20",
  },
  phone: {
    icon: Phone,
    color: "text-emerald-400",
    badgeColor: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  },
};

interface Touch {
  touch_number: number;
  channel: string;
  wait_days: number;
  subject?: string;
  body: string;
  tone_note?: string;
  purpose?: string;
}

export function TouchCard({
  touch,
  isLast,
  defaultExpanded = true,
}: {
  touch: Touch;
  isLast: boolean;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  const channel = CHANNEL_CONFIG[touch.channel] ?? CHANNEL_CONFIG.email;
  const ChannelIcon = channel.icon;
  const wordCount = touch.body?.split(/\s+/).filter(Boolean).length ?? 0;

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    const text = touch.subject
      ? `Subject: ${touch.subject}\n\n${touch.body}`
      : touch.body;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative flex gap-3">
      {/* Timeline connector */}
      <div className="flex flex-col items-center shrink-0">
        {/* Number circle */}
        <div
          className={cn(
            "h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold border-2 shrink-0",
            channel.color,
            touch.channel === "email"
              ? "border-blue-400/40 bg-blue-500/10"
              : touch.channel === "linkedin"
                ? "border-purple-400/40 bg-purple-500/10"
                : "border-emerald-400/40 bg-emerald-500/10"
          )}
        >
          {touch.touch_number}
        </div>
        {/* Vertical line */}
        {!isLast && (
          <div className="w-px flex-1 bg-clay-700 min-h-[16px]" />
        )}
      </div>

      {/* Touch content */}
      <div className="flex-1 pb-4 min-w-0">
        {/* Header — always visible */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-left flex items-center gap-2 group"
        >
          {/* Channel badge */}
          <span
            className={cn(
              "text-[10px] px-1.5 py-0.5 rounded-full font-medium border flex items-center gap-1",
              channel.badgeColor
            )}
          >
            <ChannelIcon className="h-3 w-3" />
            {touch.channel}
          </span>

          {/* Wait days */}
          {touch.wait_days > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-clay-700/50 text-clay-300">
              +{touch.wait_days}d
            </span>
          )}

          {/* Word count */}
          <span className="text-[10px] text-clay-300">
            {wordCount}w
          </span>

          {/* Expand/collapse */}
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 text-clay-300 ml-auto transition-transform opacity-0 group-hover:opacity-100",
              expanded && "rotate-180"
            )}
          />
        </button>

        {/* Body — expandable */}
        {expanded && (
          <div className="mt-2 rounded-lg border border-clay-700 bg-clay-800/30 overflow-hidden">
            {/* Subject (email only) */}
            {touch.subject && (
              <div className="px-3 py-2 border-b border-clay-700 bg-clay-800/50">
                <p className="text-[10px] text-clay-300 uppercase tracking-wider mb-0.5">
                  Subject
                </p>
                <p className="text-sm font-medium text-clay-100">
                  {touch.subject}
                </p>
              </div>
            )}

            {/* Body text */}
            <div className="px-3 py-3">
              <p className="text-sm text-clay-200 whitespace-pre-wrap leading-relaxed">
                {touch.body}
              </p>
            </div>

            {/* Footer: tone, purpose, copy */}
            <div className="px-3 py-2 border-t border-clay-700 flex items-center gap-2 flex-wrap">
              {touch.tone_note && (
                <span className="text-[10px] text-clay-300 italic">
                  {touch.tone_note}
                </span>
              )}
              {touch.purpose && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-clay-700/50 text-clay-300">
                  {touch.purpose}
                </span>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="ml-auto h-6 text-[10px] text-clay-300 hover:text-clay-100 px-1.5"
              >
                {copied ? (
                  <Check className="h-3 w-3 text-emerald-400" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
