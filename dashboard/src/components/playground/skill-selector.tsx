"use client";

import { SKILL_PILLARS } from "@/lib/constants";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function SkillSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (skill: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs text-clay-200 uppercase tracking-wider mb-1.5 font-[family-name:var(--font-sans)]">
        Skill
      </label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-full border-clay-700 bg-clay-800 text-clay-100 focus:ring-kiln-teal">
          <SelectValue placeholder="Select a skill..." />
        </SelectTrigger>
        <SelectContent className="border-clay-700 bg-clay-800">
          {Object.entries(SKILL_PILLARS).map(([pillar, skills]) => (
            <SelectGroup key={pillar}>
              <SelectLabel className="text-[11px] text-clay-300 uppercase tracking-[0.1em] px-2 py-1.5">
                {pillar}
              </SelectLabel>
              {skills.map((s) => (
                <SelectItem
                  key={s}
                  value={s}
                  className="text-clay-200 focus:bg-kiln-teal/10 focus:text-kiln-teal"
                >
                  {s}
                </SelectItem>
              ))}
            </SelectGroup>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
