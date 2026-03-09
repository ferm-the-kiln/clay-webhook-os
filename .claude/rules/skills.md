---
description: Skill authoring conventions
globs: skills/**,knowledge_base/**,clients/**
---

# Skill & Content Conventions

## Skill Files
- Each skill lives in `skills/{name}/skill.md`
- Follow the standard template: Role, Context Files to Load, Output Format, Data Fields, Rules, Examples
- Output must be valid JSON — no markdown fences, no explanation text
- Include at least 2 examples: one with rich data, one with minimal data
- Set `confidence_score` (0.0-1.0) based on available data quality

## Context References
- Use `- knowledge_base/path.md` syntax (leading dash + space)
- `{{client_slug}}` resolves from `data.client_slug` in the request
- Industry files in `knowledge_base/industries/` auto-load when `data.industry` matches

## Knowledge Base
- `knowledge_base/frameworks/` — Sales methodologies and frameworks
- `knowledge_base/voice/` — Writing style guides
- `knowledge_base/industries/` — Industry-specific context (filename = industry name)
- Files are plain markdown, injected directly into the prompt

## Client Profiles
- Stored as markdown in `clients/{slug}.md`
- Include: company name, value prop, ICP, differentiators, tone preferences
- Referenced in skills via `clients/{{client_slug}}.md`

## Full guide
See `docs/skills-guide.md` for the complete reference with templates and examples.

## Context Filtering Convention

Every skill that loads a client profile MUST have an entry in `SKILL_CLIENT_SECTIONS`
in `app/core/context_filter.py`. This is how we keep prompts tight and save tokens.

Rules:
- List ONLY the exact `##` sections your skill needs from the client profile
- There is NO shared baseline — if you don't list it, it won't load
- Persona matching is automatic: if `data.title` exists, the matching `### Persona`
  subsection loads from `## Personas` (no need to list "Personas" in your sections)
- Signal filtering is automatic: if `data.signal_type` exists, only the matching
  signal section loads from signal files (signal-openers.md, signal-taxonomy.md)
- Ask yourself: "Does the AI actually need this section to complete this specific task?"
  If the answer is no, don't include it

Example — email-gen only needs:
  ["What They Sell", "Tone Preferences", "Campaign Angles Worth Testing",
   "Campaign Angles", "Recent News & Signals"]
It does NOT need Battle Cards, Discovery Questions, ROI Framework, etc.
