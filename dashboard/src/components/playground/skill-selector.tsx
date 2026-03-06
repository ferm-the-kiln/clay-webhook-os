"use client";

import { SKILL_SAMPLES } from "@/lib/constants";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const SKILLS = Object.keys(SKILL_SAMPLES);

export function SkillSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (skill: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5 font-[family-name:var(--font-sans)]">
        Skill
      </label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-100 focus:ring-kiln-teal">
          <SelectValue placeholder="Select a skill..." />
        </SelectTrigger>
        <SelectContent className="border-clay-700 bg-clay-900">
          {SKILLS.map((s) => (
            <SelectItem
              key={s}
              value={s}
              className="text-clay-200 focus:bg-kiln-teal/10 focus:text-kiln-teal"
            >
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
