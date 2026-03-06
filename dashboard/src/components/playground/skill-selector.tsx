"use client";

import { SKILL_SAMPLES } from "@/lib/constants";

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
      <label className="block text-xs text-zinc-500 uppercase tracking-wide mb-1.5">
        Skill
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 focus:border-teal-500 focus:outline-none"
      >
        <option value="">Select a skill...</option>
        {SKILLS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
    </div>
  );
}
