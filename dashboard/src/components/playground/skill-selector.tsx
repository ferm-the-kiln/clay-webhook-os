"use client";

import { SKILL_SAMPLES } from "@/lib/constants";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const SKILLS = Object.keys(SKILL_SAMPLES);

const OUTBOUND_SKILLS = ["email-gen", "sequence-writer", "linkedin-note", "follow-up", "quality-gate"];
const ANALYZE_SKILLS = ["account-researcher", "meeting-prep", "discovery-questions", "competitive-response", "champion-enabler", "campaign-brief", "multi-thread-mapper"];

function categorizeSkills(skills: string[]) {
  const outbound = skills.filter((s) => OUTBOUND_SKILLS.includes(s));
  const analyze = skills.filter((s) => ANALYZE_SKILLS.includes(s));
  const other = skills.filter((s) => !OUTBOUND_SKILLS.includes(s) && !ANALYZE_SKILLS.includes(s));
  return { outbound, analyze, other };
}

export function SkillSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (skill: string) => void;
}) {
  const { outbound, analyze, other } = categorizeSkills(SKILLS);

  return (
    <div>
      <label className="block text-xs text-clay-500 uppercase tracking-wider mb-1.5 font-[family-name:var(--font-sans)]">
        Skill
      </label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-100 focus:ring-kiln-teal">
          <SelectValue placeholder="Select a skill..." />
        </SelectTrigger>
        <SelectContent className="border-clay-700 bg-clay-900">
          {outbound.length > 0 && (
            <SelectGroup>
              <SelectLabel className="text-[10px] text-kiln-teal uppercase tracking-wider font-semibold px-2">
                Outbound
              </SelectLabel>
              {outbound.map((s) => (
                <SelectItem
                  key={s}
                  value={s}
                  className="text-clay-200 focus:bg-kiln-teal/10 focus:text-kiln-teal"
                >
                  {s}
                </SelectItem>
              ))}
            </SelectGroup>
          )}
          {analyze.length > 0 && (
            <SelectGroup>
              <SelectLabel className="text-[10px] text-kiln-indigo uppercase tracking-wider font-semibold px-2">
                Analyze
              </SelectLabel>
              {analyze.map((s) => (
                <SelectItem
                  key={s}
                  value={s}
                  className="text-clay-200 focus:bg-kiln-indigo/10 focus:text-kiln-indigo"
                >
                  {s}
                </SelectItem>
              ))}
            </SelectGroup>
          )}
          {other.length > 0 && (
            <SelectGroup>
              <SelectLabel className="text-[10px] text-clay-500 uppercase tracking-wider font-semibold px-2">
                Other
              </SelectLabel>
              {other.map((s) => (
                <SelectItem
                  key={s}
                  value={s}
                  className="text-clay-200 focus:bg-kiln-teal/10 focus:text-kiln-teal"
                >
                  {s}
                </SelectItem>
              ))}
            </SelectGroup>
          )}
        </SelectContent>
      </Select>
    </div>
  );
}
