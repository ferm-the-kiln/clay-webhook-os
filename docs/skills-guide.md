# Skills Guide

## Available Skills

Skills are organized into two pillars:

### Content Generation

| Skill | What It Does |
|-------|-------------|
| email-gen | Cold email using PVC framework |
| sequence-writer | Multi-touch outbound sequence (5 touches) |
| linkedin-note | LinkedIn connection note (300 char limit) |
| follow-up | Follow-up email with value-add |
| quality-gate | QA review of generated content |

### Strategic Analysis

| Skill | What It Does |
|-------|-------------|
| account-researcher | Company research & video relevance assessment |
| meeting-prep | Pre-call intelligence brief |
| discovery-questions | Tailored discovery questions by persona/signal |
| competitive-response | Technical competitive displacement responses |
| champion-enabler | Internal pitch for developer champions |
| campaign-brief | Generate campaign brief with sequence |
| multi-thread-mapper | Buying committee mapping & outreach |

### Archived

The following skills have been retired to `skills/_archived/`:
`icp-scorer`, `angle-selector`, `objection-handler`, `roi-calculator`, `coordinator`, `signal-researcher`

## Adding a New Skill

1. Create `skills/{name}/skill.md`
2. Follow the standard structure (see below)
3. Test locally:
   ```bash
   curl -X POST localhost:8000/webhook \
     -H "Content-Type: application/json" \
     -d '{"skill":"name","data":{"first_name":"Test","company_name":"Acme"}}'
   ```

## Skill File Structure

Every `skill.md` follows this template:

```markdown
# Skill Name — Description

## Role
Who the AI acts as (e.g., "senior B2B copywriter")

## Context Files to Load
- knowledge_base/frameworks/some-framework.md
- knowledge_base/voice/writing-style.md
- clients/{{client_slug}}.md

## Output Format
Return ONLY valid JSON. Exact keys:
{ "key": "description", ... }

## Data Fields (flexible)
Which fields from the Clay row data are expected/optional.

## Rules
1. Specific constraints and guidelines
2. ...

## Examples

### Input:
{ ... }

### Output:
{ ... }
```

## Context Resolution

The `context_assembler` builds a 6-layer prompt:

1. **Skill content** — The full `skill.md`
2. **Knowledge base files** — Referenced via `- knowledge_base/path.md`
3. **Client context** — `clients/{{client_slug}}.md` (resolved from `data.client_slug`)
4. **Industry context** — `knowledge_base/industries/{industry}.md` (auto-loaded when `data.industry` matches a file)
5. **Instructions** — Optional `instructions` field from the request
6. **Data** — The `data` object serialized as context

## Key Rules for Skill Authors

- Context refs use `- knowledge_base/path.md` syntax (leading dash + space)
- `{{client_slug}}` is the only template variable — resolved from `data.client_slug`
- Industry files auto-load by matching `data.industry` to filenames in `knowledge_base/industries/`
- Output format must be valid JSON — no markdown, no code fences
- Include at least one example with good data and one with minimal data
- Set `confidence_score` (0.0-1.0) based on data quality when relevant

## Models

| Value | Best For |
|-------|----------|
| `opus` | Highest quality — default for all skills |
| `sonnet` | Good balance of quality and speed |
| `haiku` | Fast — classification, simple scoring |
