# Clay Webhook OS — Comprehensive Guide

> Turn Clay into a context-aware AI engine. Not just prompts — frameworks, memory, voice, and client knowledge.

---

## Table of Contents

1. [The Vision — Context Operating System](#part-1-the-vision--context-operating-system)
2. [Architecture — How It Works](#part-2-architecture--how-it-works)
3. [The Skill System — How to Think About Skills](#part-3-the-skill-system--how-to-think-about-skills)
4. [Skill Extraction — Getting Expertise Out of People's Heads](#part-4-skill-extraction--getting-expertise-out-of-peoples-heads)
5. [Plays — What You Can Build Today](#part-5-plays--what-you-can-build-today)
6. [Platform Architecture — The Vision](#part-6-platform-architecture--the-vision)
7. [Advanced Systems](#part-7-advanced-systems)
8. [Economics](#part-8-economics)
9. [Knowledge Base — What's Available](#part-9-knowledge-base--whats-available)
10. [Reference](#part-10-reference)

---

## Part 1: The Vision — Context Operating System

### What the Webhook OS Is

The Clay Webhook OS is a context-aware AI layer that sits between Clay and Claude. It transforms Clay's HTTP Actions from simple prompt-and-pray API calls into knowledge-driven, framework-calibrated, client-specific intelligence operations.

The key insight: **Clay's built-in AI (Claygent, AI columns) is stateless.** Every row starts from zero. It doesn't know your client's voice, your sales methodology, your ICP criteria, or what you learned from the last 50 campaigns. It's a blank slate every time.

The Webhook OS has **memory, voice, frameworks, and client knowledge.** It's the difference between asking a random stranger to write your emails vs. asking your best copywriter who's been on the account for six months.

### The Restaurant Analogy

| Component | Restaurant | What It Actually Is |
|-----------|-----------|---------------------|
| **Clay** | The customer placing orders | Data enrichment platform — each row is a prospect with data |
| **Webhook (POST /webhook)** | The waiter taking the order to the kitchen | HTTP request sending data from Clay to your server |
| **Express.js server** | The kitchen | Node.js server that receives requests, assembles context, calls Claude |
| **Skill file (skill.md)** | The recipe card | Instructions telling Claude exactly what to produce |
| **Knowledge base** | The pantry / ingredients | Reusable context: frameworks, industry intelligence, voice guides |
| **Client context** | The customer's preferences on file | Client-specific tone, ICP, value props, campaign angles |
| **Claude --print** | The chef | AI that reads recipe + ingredients + order → produces the dish |
| **JSON response** | The finished plate | Structured data Clay receives and maps to columns |

A random person off the street (stateless AI) might cook something edible. But a chef with your recipes, your ingredients, and your customer's preferences on file? That's a different meal entirely.

### Clay Built-In vs Webhook OS

| Dimension | Clay Built-In AI | Webhook OS |
|-----------|-----------------|------------|
| **State** | Stateless — every row starts from zero | Knowledge-loaded — frameworks, voice, client context injected every time |
| **Voice** | Generic AI-sounding output | Calibrated to client's writing style, tone preferences, anti-patterns |
| **Methodology** | Single prompt, hope for the best | Framework-driven (PVC, MEDDIC, etc.) — structured reasoning |
| **Client knowledge** | None — doesn't know who you're writing for | Client file loaded per request — ICP, value prop, campaign angles |
| **Industry awareness** | Generic | Auto-loads industry context (SaaS, fintech, healthtech) based on prospect data |
| **Quality control** | You get what you get | Confidence scoring, structured JSON schemas, validation |
| **Iteration** | Edit the prompt, re-run | Edit the skill file or knowledge base — affects all future rows |
| **Cost model** | Clay credits per enrichment | Claude Code Max subscription — flat rate, unlimited |
| **Extensibility** | Limited to Clay's UI | Drop a file, get a new skill — no code changes |

### Why This Matters

When you're running outbound for a client, the difference between a 2% reply rate and a 5% reply rate isn't the AI model — it's the context. It's knowing that this client's ICP is VP Sales at Series B SaaS companies. It's knowing their tone is "casual-professional, never salesy." It's knowing to lead with the PVC framework, not AIDA. It's knowing that "leverage" and "synergy" are banned words.

The Webhook OS makes that context automatic. Write it once, use it on every row.

---

## Part 2: Architecture — How It Works

### End-to-End Flow

```
Clay Row                Your Server (Replit)              Claude
─────────              ────────────────────              ──────

┌─────────────┐        ┌──────────────────┐
│ Sarah        │        │ POST /webhook     │
│ VP Sales     │───────▶│                   │
│ Acme, SaaS   │  HTTP  │ 1. Auth check     │
│ Series D     │  POST  │ 2. Load skill.md  │
└─────────────┘        │ 3. Load knowledge │
                        │ 4. Load client ctx│
                        │ 5. Auto-load      │
                        │    industry ctx   │
                        │ 6. Build prompt   │        ┌─────────────┐
                        │ 7. Spawn claude   │───────▶│ claude      │
                        │    --print        │ stdin  │ --print     │
                        │                   │        │ --model     │
                        │                   │◀───────│ haiku       │
                        │ 8. Parse JSON     │ stdout │             │
┌─────────────┐        │ 9. Return to Clay │        └─────────────┘
│ email_subject│◀───────│                   │
│ email_body   │  JSON  └──────────────────┘
│ confidence   │
└─────────────┘
```

### Step by Step

1. **Clay has a row:** "Sarah, VP Sales, Acme, SaaS, Series D"
2. **Clay's HTTP Action** sends a POST request to your webhook URL
3. **Express server** receives the request, validates auth
4. **Server reads the skill file** (`skills/email-gen/skill.md`)
5. **Server parses context refs** from the skill and loads knowledge files
6. **Server resolves `{{client_slug}}`** — loads client-specific context
7. **Server auto-loads industry context** — matches `data.industry` to files in `knowledge_base/industries/`
8. **Server assembles the full prompt** — system instructions + skill + knowledge + client + data + campaign instructions
9. **Server spawns `claude --print`** as a child process, pipes the prompt via stdin
10. **Claude generates JSON** following the skill's output format
11. **Server parses the JSON**, adds metadata (`_skill`, `_engine`), returns to Clay
12. **Clay maps the JSON** to columns on the row

### Monorepo Structure

```
clay-webhook-os/
├── index.js                       # Express server + Claude CLI wrapper
├── package.json                   # Dependencies (express only)
├── CLAUDE.md                      # Setup & architecture reference
├── WEBHOOK-OS-GUIDE.md            # This guide
│
├── skills/                        # Skill definitions
│   └── email-gen/
│       └── skill.md               # PVC cold email generator
│
├── knowledge_base/                # Reusable knowledge (injected into prompts)
│   ├── frameworks/
│   │   └── josh-braun-pvc.md      # PVC email framework
│   ├── voice/
│   │   └── writing-style.md       # Tone and voice rules
│   └── industries/
│       └── saas-b2b.md            # SaaS B2B industry context (auto-loaded)
│
├── clients/                       # Per-client context files
│   └── _template.md               # Template for new clients
│
├── _system/
│   └── knowledge_graph/
│       ├── taxonomy.yaml          # Blessed tags and domains
│       └── ontology.yaml          # How knowledge nodes relate
│
├── 00_foundation/                 # Positioning & messaging docs
├── .replit                        # Replit run/deploy config
└── replit.nix                     # Nix environment (Node.js 20)
```

### Key Components

#### Express Server (`index.js`)

A minimal Express server (~300 lines) with four responsibilities:

1. **Route handling** — `/webhook` (main), `/health`, `/skills`, `/test-echo`
2. **Skill loading** — reads `skills/[name]/skill.md` from the filesystem
3. **Context assembly** — parses skill file for context refs, loads knowledge + client files, auto-loads industry context
4. **Claude CLI wrapper** — spawns `claude --print` as a subprocess, pipes the assembled prompt via stdin, collects JSON from stdout

#### Claude CLI Wrapper (`callClaude`)

```javascript
function callClaude(prompt, { model = "haiku", timeoutMs = 55000 } = {})
```

- Spawns `claude --print --output-format text --model [model] --max-turns 1 -`
- Cleans the `CLAUDECODE` env var to avoid nested-session errors
- Pipes the full prompt via stdin (no command-line length limits)
- 55-second timeout guard (Clay's HTTP Action timeout is ~100 seconds)
- Returns raw stdout text, caller handles JSON parsing

#### Context Assembly (`buildFullPrompt`)

The prompt assembly follows a strict hierarchy:

```
┌─────────────────────────────────────────┐
│ 1. SYSTEM INSTRUCTIONS                  │
│    "You are a JSON generation engine.   │
│     Return ONLY valid JSON..."          │
├─────────────────────────────────────────┤
│ 2. SKILL INSTRUCTIONS                   │
│    (full contents of skill.md)          │
│    Role, rules, output format, examples │
├─────────────────────────────────────────┤
│ 3. LOADED CONTEXT                       │
│    ## knowledge_base/frameworks/pvc.md  │
│    ## knowledge_base/voice/style.md     │
│    ## clients/twelve-labs.md            │
│    ## knowledge_base/industries/saas.md │
├─────────────────────────────────────────┤
│ 4. DATA TO PROCESS                      │
│    { "first_name": "Sarah", ... }       │
├─────────────────────────────────────────┤
│ 5. CAMPAIGN INSTRUCTIONS (optional)     │
│    "Focus on the funding round angle.." │
├─────────────────────────────────────────┤
│ 6. FINAL INSTRUCTION                    │
│    "Return ONLY the JSON object."       │
└─────────────────────────────────────────┘
```

Each layer adds specificity. System sets the output constraint. Skill defines the task. Knowledge provides expertise. Client adds personalization. Data provides the prospect. Instructions add campaign-level overrides.

### Routes Reference

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/` | Service info (status, engine) | No |
| GET | `/health` | Health check with timestamp | No |
| GET | `/skills` | List available skill names | No |
| POST | `/test-echo` | Echo back request body for debugging | No |
| POST | `/webhook` | Main endpoint — runs a skill with data | Optional (X-API-Key) |

### Webhook Request Format

```json
{
  "skill": "email-gen",
  "data": {
    "first_name": "Sarah",
    "company_name": "Acme",
    "title": "VP Sales",
    "industry": "SaaS",
    "signal_type": "funding",
    "signal_detail": "Series D, $175M",
    "client_slug": "twelve-labs"
  },
  "instructions": "Focus on the scaling challenge post-raise",
  "model": "haiku"
}
```

- `skill` (required): Name of the skill directory
- `data` (required): Object with prospect data — fields are flexible per skill
- `instructions` (optional): Campaign-level overrides
- `model` (optional): `haiku` (default), `sonnet`, or `opus`

---

## Part 3: The Skill System — How to Think About Skills

### Mental Model: Skills = Your Brain On Paper

A skill file is everything a smart junior would need to do your job on one specific task. Not a vague prompt — a complete set of instructions with role, knowledge references, rules, output format, and examples.

The formula:

```
WHO (role) + WHAT (knowledge) + HOW (rules/logic) + OUTPUT (JSON schema) = Skill
```

### The Litmus Test

Before writing a skill, ask: **"Would I give these instructions to a smart junior and expect the right output?"**

If the answer is "they'd need to ask me a bunch of questions" — your skill needs more detail.
If the answer is "they could figure it out" — your skill is probably ready.

### The 6 Layers of Context

Every prompt assembled by the server has up to 6 layers:

| Layer | Source | Purpose |
|-------|--------|---------|
| **System** | Hardcoded in `buildFullPrompt` | JSON-only constraint, output discipline |
| **Skill** | `skills/[name]/skill.md` | Role, task definition, rules, output format, examples |
| **Knowledge** | `knowledge_base/frameworks/`, `voice/` | Methodologies, writing guides, patterns |
| **Client** | `clients/[slug].md` | Value prop, ICP, tone preferences, campaign angles |
| **Data** | `req.body.data` | The prospect's information from Clay |
| **Direction** | `req.body.instructions` | Campaign-specific overrides from the user |

Each layer is independent. You can swap frameworks without changing skills. You can swap clients without changing knowledge. You can change campaign direction without touching anything permanent.

### What Makes a Good Skill

**Good skills are:**
- **Specific** — one clear task with one clear output
- **Self-contained** — all instructions in the file, no implicit assumptions
- **Flexible on input** — gracefully handle missing fields (confidence scoring)
- **Strict on output** — exact JSON schema, no deviation
- **Example-driven** — at least 2 examples (high-data and low-data scenarios)

**Bad skills are:**
- **Vague** — "write something good" (no structure, no rules)
- **Over-broad** — tries to do 5 things in one skill (score AND write AND analyze)
- **Input-fragile** — breaks when a field is missing
- **Output-ambiguous** — "return a response" (what shape? what fields?)

### Anatomy of a Skill File

Using `email-gen` as the reference:

```markdown
# Email Generator — Cold Outbound (Josh Braun PVC)

## Role
You are a senior B2B copywriter who writes cold emails using Josh Braun's
PVC framework. You write like a human — short, specific, and genuinely
helpful. Never salesy.

## Context Files to Load
- knowledge_base/frameworks/josh-braun-pvc.md
- knowledge_base/voice/writing-style.md
- clients/{{client_slug}}.md

## Output Format
Return ONLY valid JSON. No markdown, no explanation.
Exact keys required:
{
  "email_subject": "string, max 50 chars, lowercase, no clickbait",
  "email_body": "string, plain text, 3-5 sentences max",
  "personalization_hook": "string, the specific detail you referenced",
  "framework_notes": "string, how PVC was applied",
  "confidence_score": "number 0.0-1.0"
}

## Rules
1. Subject line: lowercase, conversational, under 50 chars
2. Opening: reference something SPECIFIC about them
3. Never use: "I hope this finds you well", "reaching out", "synergy"
4. Never mention AI or automation
5. Keep under 75 words total
6. CTA must be low-commitment
7. Match tone to industry
8. If data insufficient, set confidence_score < 0.5

## Examples
[High-data example with all fields → 0.92 confidence]
[Low-data example with minimal fields → 0.45 confidence]
```

### How to Add a New Skill

1. Create the directory: `skills/[name]/`
2. Create the skill file: `skills/[name]/skill.md`
3. Define all 5 sections: Role, Context Files, Output Format, Rules, Examples
4. Test with curl:
```bash
curl -X POST "https://<your-domain>/webhook" \
  -H "Content-Type: application/json" \
  -d '{"skill":"your-skill","data":{"first_name":"Test","company_name":"Acme"}}'
```
5. Connect to Clay once it returns valid JSON

**No server restart needed. No code changes.** Drop a file, it works. The server discovers skills by reading the `skills/` directory at request time.

---

## Part 4: Skill Extraction — Getting Expertise Out of People's Heads

### The Core Problem

The hardest part of building skills isn't the code — it's the knowledge. The people who know how to write great cold emails, score leads, or prep for meetings have internalized their expertise so deeply that they can't articulate it on demand. Ask them "how do you write a good cold email?" and you'll get vague answers. Watch them write one and you'll see magic.

This is the **extraction problem**: turning implicit expertise into explicit instructions that Claude can follow.

### 6 Extraction Methods

#### Method 1: The Red Pen Method

**What:** Show them AI-generated output and let them tear it apart.

**How:**
1. Generate 5-10 sample outputs using a basic prompt
2. Print them out (or share in a doc)
3. Ask: "Mark everything that's wrong. Be brutal."
4. Their corrections reveal the rules they can't articulate

**Why it works:** People are better at critiquing than creating from scratch. They can't tell you what good looks like, but they instantly know what bad looks like.

**Example:**
- AI writes: "I hope this email finds you well. I wanted to reach out because..."
- Expert marks: "DELETE. Never open with this. Reference something specific about them."
- Extracted rule: "Never use 'I hope this finds you well' or 'reaching out.' Open with a specific reference to their company, role, or recent activity."

#### Method 2: The Fork-in-the-Road Method

**What:** Give them the same prospect with different variables and ask what changes.

**How:**
1. Present: "Same company, but the prospect is a VP Sales vs. a CTO — what changes?"
2. Present: "Same person, but they just raised funding vs. they just had layoffs — what changes?"
3. The differences reveal their decision logic

**Why it works:** Variation forces the expert to surface their decision trees. When everything's the same, they operate on autopilot. When something changes, they have to explain why.

**Example:**
- "VP Sales at a Series B SaaS company" → casual, pipeline-focused angle
- "CTO at a Series B SaaS company" → more technical, efficiency-focused angle
- Extracted rule: "Match angle to persona: Sales leaders care about pipeline and quota. Technical leaders care about efficiency and integration."

#### Method 3: The "Show Me Your Best One" Method

**What:** Collect their actual best work and reverse-engineer the patterns.

**How:**
1. Ask: "Show me the 3 best cold emails you've ever sent that got replies"
2. Ask: "What made these work?"
3. Look for patterns across all three — that's the formula

**Why it works:** Real results beat theoretical knowledge. Their best work contains the patterns they follow instinctively but can't describe.

**Example:**
- Email 1: Led with a funding announcement, 3 sentences, question CTA
- Email 2: Led with a job posting signal, 4 sentences, "worth exploring?" CTA
- Email 3: Led with a mutual connection reference, 2 sentences, casual CTA
- Pattern: Always leads with a SPECIFIC external signal. Always under 5 sentences. Always a question CTA, never a demand.

#### Method 4: The Negative Space Method

**What:** Ask what makes them cringe. What would they NEVER do?

**How:**
1. Ask: "What's the worst cold email you've ever received? Why?"
2. Ask: "What words or phrases should NEVER appear in our emails?"
3. Ask: "What's the #1 mistake you see juniors make?"

**Why it works:** Anti-patterns are often more actionable than positive rules. "Never do X" is clearer than "try to do Y."

**Example:**
- "I cringe when I see 'leverage' or 'synergy' — it screams template"
- "Never start with 'I' — makes it about you, not them"
- "If someone uses 'at the end of the day' I stop reading"
- Extracted rules: Banned word list + structural rules (don't start with "I")

#### Method 5: The Apprentice Method

**What:** Ask them to teach you how to do it, not describe how they do it.

**How:**
1. Say: "Pretend I'm your new hire. Teach me to write cold emails for this client."
2. Record everything — they'll be more structured in teaching mode
3. Their teaching sequence reveals their mental model

**Why it works:** Teaching mode activates a different part of the brain than describing mode. When teaching, people organize information into learnable steps. When describing, they jump around.

**Example:**
- "First, look at what they just did — funding round? New hire? Product launch?"
- "Then figure out what that means for them — scaling pain? new priorities?"
- "Now connect what we do to that specific situation"
- Extracted framework: Signal → Implication → Connection

#### Method 6: The Live Ride-Along

**What:** Watch them work in real time. Interrupt at decision points.

**How:**
1. Screen share — watch them write an email, score a lead, or prep for a call
2. Every time they pause or make a choice, ask: "What are you thinking right now?"
3. Every time they skip something, ask: "Why did you skip that?"

**Why it works:** This captures the unconscious decisions that other methods miss. The pauses, the skips, the gut reactions — that's where the real expertise lives.

**Example:**
- They skip a prospect: "Why?" → "Company's too small. Under 50 employees, it's not worth it for this client."
- They pause on a subject line: "What are you deciding?" → "Whether to reference the funding or the new VP hire. Funding is safer."
- Extracted rules: Minimum company size threshold + signal priority ranking

### The Extraction Stack (Recommended 3-Session Sequence)

| Session | Method | Duration | Goal |
|---------|--------|----------|------|
| **Session 1** | "Show Me Your Best" + Negative Space | 45 min | Collect examples, anti-patterns, banned words |
| **Session 2** | Fork-in-the-Road + Red Pen | 60 min | Surface decision logic, validate with AI-generated drafts |
| **Session 3** | Live Ride-Along | 30 min | Capture unconscious decisions, fill gaps |

After 3 sessions you'll have enough to write a skill file that captures 80%+ of their expertise. The remaining 20% emerges through iteration — run the skill, show them output, refine.

### Client Framing: How to Pitch the Extraction Process

Don't say "we need to extract your knowledge." Say:

> "We're going to build a system that writes emails the way YOU would write them. Not generic AI — YOUR voice, YOUR frameworks, YOUR judgment. We need about 3 short sessions to capture how you think about this. Then the system handles the volume while you handle the strategy."

The value pitch: **"You're not being replaced. You're being cloned for the boring parts."**

---

## Part 5: Plays — What You Can Build Today

Each play below = 1 skill file. Drop it in `skills/[name]/skill.md` and it works.

### Play 1: ICP Scorer with Reasoning

**What Clay sends:**
```json
{
  "skill": "icp-scorer",
  "data": {
    "company_name": "Lattice",
    "industry": "HR Tech",
    "employee_count": 850,
    "funding_stage": "Series D",
    "tech_stack": ["Salesforce", "Outreach", "6sense"],
    "title": "VP Sales",
    "client_slug": "twelve-labs"
  }
}
```

**What comes back:**
```json
{
  "icp_score": 87,
  "tier": "A",
  "reasoning": "Strong fit: HR Tech SaaS in scaling stage (Series D, 850 employees). Tech stack shows GTM maturity (Salesforce + Outreach + 6sense). VP Sales title matches decision-maker profile.",
  "strengths": ["Right industry vertical", "Decision-maker title", "Mature GTM stack"],
  "gaps": ["No hiring signal detected", "No direct intent data"],
  "recommended_angle": "scaling-post-raise",
  "confidence_score": 0.82
}
```

**Why it's valuable:** Clay's built-in scoring is generic. This scores against YOUR client's actual ICP definition, loaded from their client context file. The reasoning field explains WHY — useful for reps reviewing the list.

### Play 2: Signal-Based Angle Selector

**What Clay sends:**
```json
{
  "skill": "angle-selector",
  "data": {
    "company_name": "Lattice",
    "signals": [
      {"type": "funding", "detail": "Series D, $175M", "date": "2026-02-15"},
      {"type": "hiring", "detail": "3 SDR postings on LinkedIn", "date": "2026-02-20"},
      {"type": "tech_change", "detail": "Added Outreach to stack", "date": "2026-01-10"}
    ],
    "title": "VP Sales",
    "client_slug": "twelve-labs"
  }
}
```

**What comes back:**
```json
{
  "selected_angle": "scaling-post-raise",
  "angle_rationale": "Series D is most recent and highest-impact. Hiring SDRs confirms scaling investment. Lead with funding, reinforce with hiring.",
  "backup_angle": "outbound-infrastructure",
  "signal_freshness": "high",
  "signals_used": ["funding", "hiring"],
  "signals_skipped": [{"type": "tech_change", "reason": "Too old (7+ weeks) and lower impact than funding"}],
  "confidence_score": 0.88
}
```

**Why it's valuable:** When a prospect has 3+ signals, which one do you lead with? This skill applies signal priority logic — recency, impact, relevance to the client's value prop — and picks the best angle with reasoning.

### Play 3: LinkedIn Connection Note Generator

**What Clay sends:**
```json
{
  "skill": "linkedin-note",
  "data": {
    "first_name": "Sarah",
    "title": "VP Sales",
    "company_name": "Lattice",
    "mutual_connections": 3,
    "recent_post_topic": "Scaling SDR teams without burning out managers",
    "signal_detail": "Series D raise",
    "client_slug": "twelve-labs"
  }
}
```

**What comes back:**
```json
{
  "connection_note": "Sarah — your post on scaling SDRs without burning out managers hit home. We're working on exactly that problem with a few HR Tech teams post-raise. Would love to compare notes.",
  "note_length": 42,
  "pattern_used": "content-engagement",
  "personalization_element": "Referenced her LinkedIn post topic",
  "confidence_score": 0.85
}
```

**Why it's valuable:** LinkedIn connection notes have a 300-character limit. Every word matters. This skill applies the right pattern (mutual connection, content engagement, event-based, direct value, shared background) based on what data is available.

### Play 4: Objection Handler Generator

**What Clay sends:**
```json
{
  "skill": "objection-handler",
  "data": {
    "objection": "We already use Outreach for our outbound",
    "prospect_context": {
      "company_name": "Lattice",
      "title": "VP Sales",
      "current_tools": ["Outreach", "Salesforce"]
    },
    "client_slug": "twelve-labs"
  }
}
```

**What comes back:**
```json
{
  "response": "Makes total sense — Outreach is great for execution. The question is whether the emails going INTO Outreach are personalized enough to actually get replies. That's the layer we add. Most teams using Outreach see 2-3x reply rates when the copy is signal-driven rather than template-driven.",
  "strategy": "reframe-complement",
  "key_distinction": "Execution tool vs. intelligence layer — we're not replacing Outreach, we're feeding it better inputs",
  "follow_up_question": "What's your current reply rate on cold sequences?",
  "confidence_score": 0.78
}
```

**Why it's valuable:** Pre-arms reps with responses to common objections, calibrated to the specific tool the prospect mentions and your client's positioning.

### Play 5: Meeting Prep Card Generator

**What Clay sends:**
```json
{
  "skill": "meeting-prep",
  "data": {
    "first_name": "Sarah",
    "title": "VP Sales",
    "company_name": "Lattice",
    "industry": "HR Tech",
    "employee_count": 850,
    "funding_stage": "Series D",
    "recent_news": "Raised $175M, expanding enterprise segment",
    "linkedin_summary": "15 years in SaaS sales, prev Salesforce and HubSpot",
    "meeting_type": "discovery",
    "client_slug": "twelve-labs"
  }
}
```

**What comes back:**
```json
{
  "prep_card": {
    "prospect_summary": "Sarah is VP Sales at Lattice (HR Tech, 850 employees, Series D). 15-year SaaS sales veteran with enterprise experience from Salesforce and HubSpot. Currently expanding Lattice's enterprise segment post-raise.",
    "key_talking_points": [
      "Enterprise scaling post-raise — she's lived this at Salesforce, knows the playbook",
      "Outbound infrastructure for the next growth stage",
      "Data quality as the foundation for personalized outreach at scale"
    ],
    "questions_to_ask": [
      "How is the enterprise expansion going post-raise?",
      "What does your current outbound motion look like?",
      "Where are you feeling the most friction in pipeline generation?"
    ],
    "landmines_to_avoid": [
      "Don't oversimplify — she's experienced and will see through surface-level pitches",
      "Don't bash Salesforce or HubSpot — she worked there"
    ],
    "rapport_builders": [
      "Her Salesforce background — enterprise scaling is a shared language",
      "The fundraise — genuine congratulations + specific follow-up"
    ]
  },
  "confidence_score": 0.85
}
```

**Why it's valuable:** Turns Clay enrichment data into an actual call prep card. Reps go into meetings knowing what to say, what to ask, and what to avoid — all calibrated to the client's value prop.

### Play 6: Post-Call Follow-Up Generator

**What Clay sends:**
```json
{
  "skill": "follow-up",
  "data": {
    "first_name": "Sarah",
    "company_name": "Lattice",
    "meeting_notes": "Discussed outbound scaling challenges. She's hiring 5 SDRs but worried about ramp time. Interested in seeing how we handle personalization at scale. Wants to loop in her RevOps lead Marcus.",
    "next_steps": ["Send case study on SDR ramp reduction", "Schedule follow-up with Marcus"],
    "client_slug": "twelve-labs"
  }
}
```

**What comes back:**
```json
{
  "follow_up_email": {
    "subject": "lattice + scaling outbound — next steps",
    "body": "Sarah — great conversation today. The SDR ramp challenge is real, especially when you're hiring 5 at once.\n\nAttached is a case study from a similar-stage HR Tech company that cut ramp time by 40% using signal-driven personalization instead of template-based sequences.\n\nHappy to walk through this with you and Marcus when it makes sense. What does his calendar look like next week?",
    "tone_match": "casual-professional, matches client voice"
  },
  "action_items_extracted": [
    {"action": "Send SDR ramp case study", "owner": "us", "due": "today"},
    {"action": "Schedule follow-up with Marcus", "owner": "us", "due": "this week"}
  ],
  "confidence_score": 0.90
}
```

**Why it's valuable:** Follow-ups within 2 hours of a meeting have 3x the response rate. This skill turns raw meeting notes into a polished follow-up email + extracted action items, in the client's voice.

### Play 7: Campaign Brief Generator (Meta Play)

**What Clay sends:**
```json
{
  "skill": "campaign-brief",
  "data": {
    "client_slug": "twelve-labs",
    "target_icp": "VP Sales at Series B-D SaaS companies, 200-2000 employees",
    "campaign_goal": "Book 15 meetings this month",
    "available_signals": ["funding", "hiring", "tech_stack", "job_postings"],
    "channel": "email + linkedin"
  }
}
```

**What comes back:**
```json
{
  "campaign_brief": {
    "name": "Twelve Labs — Series B-D SaaS Outbound Q1",
    "target_definition": "VP Sales / CRO at B2B SaaS companies, Series B-D, 200-2000 employees",
    "primary_angles": [
      {"angle": "post-raise-scaling", "signal": "funding", "message": "Scaling outbound post-raise without proportional headcount growth"},
      {"angle": "sdr-productivity", "signal": "hiring", "message": "Making new SDR hires productive faster with signal-driven sequences"},
      {"angle": "stack-optimization", "signal": "tech_stack", "message": "Getting more from existing GTM stack through better data and personalization"}
    ],
    "sequence_structure": {
      "touches": 5,
      "channels": ["email", "linkedin"],
      "cadence": "Day 1 email → Day 3 LinkedIn → Day 5 email → Day 8 LinkedIn → Day 12 email"
    },
    "volume_math": {
      "target_meetings": 15,
      "estimated_reply_rate": "4%",
      "estimated_meeting_conversion": "25%",
      "prospects_needed": 1500
    },
    "skills_to_chain": ["icp-scorer", "angle-selector", "email-gen", "linkedin-note"]
  },
  "confidence_score": 0.75
}
```

**Why it's valuable:** This is the meta play — it generates the campaign strategy that other skills execute. The `skills_to_chain` field tells you exactly which skills to wire up in Clay.

### The Killer Combo: Manual Chaining in Clay

Today, you chain skills manually in Clay by creating multiple HTTP Action columns:

```
Column 1: ICP Score    → POST /webhook {"skill": "icp-scorer", ...}
Column 2: Angle        → POST /webhook {"skill": "angle-selector", ...}
Column 3: Email        → POST /webhook {"skill": "email-gen", "instructions": "/Angle Column"}
Column 4: LinkedIn     → POST /webhook {"skill": "linkedin-note", ...}
```

Each column feeds the next. The ICP score filters low-fit prospects. The angle selector picks the best signal. The email generator uses that angle. The LinkedIn note complements the email.

This is the power of the system: **each skill is a building block.** Compose them in any order for any campaign.

---

## Part 6: Platform Architecture — The Vision

### Current State

```
┌─────────┐     ┌────────────────────┐     ┌──────────┐
│  Clay    │────▶│  Express Server    │────▶│  Claude   │
│  (rows)  │     │  (single webhook)  │     │  (1 call) │
│          │◀────│                    │◀────│           │
└─────────┘     └────────────────────┘     └──────────┘

- 1 skill at a time
- Manual chaining via Clay columns
- Single model per request
- No outcome tracking
- No deduplication
```

### Target State

```
┌─────────┐     ┌──────────────────────────────────────┐     ┌──────────┐
│  Clay    │────▶│  Webhook OS Platform                  │────▶│  Claude   │
│  (rows)  │     │  ┌─────────────┐  ┌───────────────┐ │     │  (multi)  │
│          │     │  │ Pipeline    │  │ Context       │ │     │  haiku    │
│          │     │  │ Router      │──│ Assembler     │ │     │  sonnet   │
│          │     │  └─────────────┘  └───────────────┘ │     │  opus     │
│          │     │  ┌─────────────┐  ┌───────────────┐ │     └──────────┘
│          │     │  │ Chain       │  │ Quality       │ │
│          │     │  │ Runner      │  │ Gate          │ │
│          │     │  └─────────────┘  └───────────────┘ │
│          │     │  ┌─────────────┐  ┌───────────────┐ │     ┌──────────┐
│          │     │  │ Dedup       │  │ Learning      │ │────▶│  Portal   │
│          │◀────│  │ Brain       │  │ Loop          │ │     │  (review) │
└─────────┘     │  └─────────────┘  └───────────────┘ │     └──────────┘
                └──────────────────────────────────────┘
```

### Skill Chaining Engine

The core upgrade: a pipeline router that runs multiple skills in sequence, passing output from one as input to the next.

#### Pipeline Definitions

```json
{
  "name": "full-outbound",
  "description": "Score → Angle → Email → LinkedIn",
  "steps": [
    {"skill": "icp-scorer", "model": "haiku", "filter": {"min_score": 60}},
    {"skill": "angle-selector", "model": "haiku"},
    {"skill": "email-gen", "model": "sonnet"},
    {"skill": "linkedin-note", "model": "haiku"}
  ]
}
```

**Key design decisions:**
- Each step specifies its own model — scoring on Haiku (fast/cheap), creative writing on Sonnet (better quality)
- Filter steps can halt the pipeline — if ICP score < 60, don't waste tokens generating an email
- Each step's output merges into the data object for the next step
- Final response includes all outputs from all steps

#### Pipeline Endpoint

```
POST /pipeline
{
  "pipeline": "full-outbound",
  "data": { ... },
  "instructions": "..."
}
```

Single request, multiple skills, one JSON response back to Clay.

### Portal Bridge

The Webhook OS connects to a client portal for review and approval workflows:

```
Webhook OS generates:
  → Email drafts
  → LinkedIn notes
  → Campaign briefs

Portal displays:
  → "Review these 50 emails before they go to Outreach"
  → Client approves/edits
  → Approved content pushed to execution
```

This is where human-in-the-loop meets AI scale. Generate 500 emails, review the top 50, approve with one click.

### Target Monorepo Structure

```
clay-webhook-os/
├── index.js                       # Express server + routes
├── lib/
│   ├── claude.js                  # Claude CLI wrapper
│   ├── context.js                 # Context assembly
│   ├── pipeline.js                # Chain runner
│   ├── dedup.js                   # Deduplication brain
│   └── quality.js                 # Quality gate
│
├── skills/                        # Skill definitions (unchanged)
│   ├── email-gen/skill.md
│   ├── icp-scorer/skill.md
│   ├── angle-selector/skill.md
│   ├── linkedin-note/skill.md
│   ├── objection-handler/skill.md
│   ├── meeting-prep/skill.md
│   ├── follow-up/skill.md
│   └── campaign-brief/skill.md
│
├── pipelines/                     # Pipeline definitions (JSON configs)
│   ├── full-outbound.json
│   ├── score-and-email.json
│   └── meeting-prep-suite.json
│
├── knowledge_base/                # Unchanged
├── clients/                       # Unchanged
├── outcomes/                      # Learning loop data
│   └── [skill]/results.jsonl
└── _system/                       # Unchanged
```

---

## Part 7: Advanced Systems

### The Learning Loop

**Problem:** You generate 1,000 emails but never learn which ones worked.

**Solution:** Track outcomes (replied, opened, bounced, meeting booked) and feed them back into skill optimization.

```
Generate email → Send via Outreach → Track outcome → Feed back to skill

outcomes/email-gen/results.jsonl:
{"prospect": "Sarah", "company": "Lattice", "confidence": 0.92, "outcome": "replied", "meeting": true}
{"prospect": "Mike", "company": "Acme", "confidence": 0.45, "outcome": "no_reply", "meeting": false}
```

Over time, patterns emerge: which signals correlate with replies? Which confidence scores predict meetings? Which angles work for which industries? The skill evolves from "best practices" to "data-driven."

### The Dedup Brain

**Problem:** You're running 3 campaigns for the same client. The same company shows up in all three. Three different angles. Three different emails. The prospect gets all three. They think you're spam.

**Solution:** A dedup layer that tracks which company-angle combinations have been used and ensures variety.

```json
{
  "company": "Lattice",
  "client": "twelve-labs",
  "angles_used": [
    {"angle": "post-raise-scaling", "date": "2026-02-15", "campaign": "q1-outbound"},
    {"angle": "sdr-productivity", "date": "2026-02-28", "campaign": "q1-linkedin"}
  ],
  "angles_available": ["stack-optimization", "market-expansion"]
}
```

When the angle-selector skill runs, it checks the dedup store and avoids angles already used for that company. Fresh angle every time.

### The Context Mesh

**Problem:** Your knowledge base is static files. But you also have call recordings, email threads, CRM notes, and interaction history. That context is trapped in other systems.

**Solution:** A context mesh that pulls real-time context from multiple sources:

```
Knowledge Base (static)
  + Fathom Call Intelligence (dynamic)
  + CRM Last Activity (dynamic)
  + Interaction History (dynamic)
  + Knowledge Graph (relationships)
  = Full Context Mesh
```

Before generating an email for a prospect at Lattice, the mesh checks: "Have we talked to anyone at Lattice before? What was the outcome? What did we learn?" That context gets injected into the prompt alongside the static knowledge.

### The Quality Gate

**Problem:** 95% of generated output is good enough. 5% has weird phrasing, AI-sounding language, or factual errors. You don't want to review every row manually.

**Solution:** A quality gate — an AI copy editor as the final step in any chain.

```json
{
  "skill": "quality-gate",
  "checks": [
    "No AI-sounding phrases (delve, leverage, it's important to note)",
    "No factual claims that aren't supported by the data",
    "Subject line under 50 chars",
    "Email body under 75 words",
    "CTA is a question, not a demand",
    "Confidence score aligns with data quality"
  ],
  "actions": {
    "pass": "return as-is",
    "soft_fail": "return with quality_warnings array",
    "hard_fail": "return error with specific issues"
  }
}
```

Run on Haiku (cheap) after the creative step (Sonnet). Catches the 5% before it goes to the client.

### The Signal Stack Ranker

**Problem:** A prospect has 5 signals — funding, hiring, tech change, news mention, job posting. Which one do you lead with?

**Solution:** A signal ranking system that considers:

| Factor | Weight | Logic |
|--------|--------|-------|
| Recency | 30% | Signals decay — a funding round from last week > one from 3 months ago |
| Impact | 25% | Funding > job posting. Executive hire > individual contributor hire |
| Relevance | 25% | How well does this signal connect to the client's value prop? |
| Uniqueness | 20% | If everyone's referencing the funding round, lead with something else |

The angle-selector skill applies this logic, but a dedicated ranker could make it more explicit and data-driven.

### Skill Versioning + A/B Testing

**Problem:** You want to test whether PVC or AIDA writes better emails. But you can't run both simultaneously.

**Solution:** Skill versioning with random assignment:

```
skills/
├── email-gen/
│   ├── skill.md          # Current default (PVC)
│   ├── skill.v2.md       # AIDA variant
│   └── config.json       # {"ab_test": true, "split": 50}
```

50% of rows get PVC, 50% get AIDA. Track outcomes per version. After 500 rows, the data tells you which framework works better for this client's ICP.

### Content Repurposing Engine

**Problem:** You wrote a great cold email. Now you need a LinkedIn note, a follow-up sequence, and a voicemail script. Rewriting from scratch wastes time and risks inconsistency.

**Solution:** One input, multiple outputs:

```json
{
  "pipeline": "content-repurpose",
  "steps": [
    {"skill": "email-gen", "model": "sonnet"},
    {"skill": "linkedin-note", "model": "haiku", "input": "use email output as source"},
    {"skill": "voicemail-script", "model": "haiku", "input": "use email output as source"},
    {"skill": "follow-up-sequence", "model": "sonnet", "input": "use email output as source"}
  ]
}
```

One Clay column, four outputs. Consistent angle and messaging across all channels.

### The "Who Should I Talk To Next" Ranker

**Problem:** You have 200 prospects in a Clay table. Where do you start?

**Solution:** A meta-skill that ranks prospects by "likelihood of productive conversation":

```json
{
  "rank_score": 92,
  "reasoning": "High ICP fit (87), fresh funding signal (2 weeks old), VP Sales title (decision maker), mutual connection exists, no prior outreach from us",
  "recommended_action": "Send personalized email + LinkedIn connection request",
  "urgency": "high — funding signal decays quickly"
}
```

This combines ICP score, signal freshness, relationship proximity, and outreach history into a single "talk to this person next" ranking.

---

## Part 8: Economics

### Cost Per Model

The Webhook OS uses your Claude Code Max subscription, which means flat-rate pricing regardless of usage. However, understanding the per-call economics helps with model selection and client pricing.

| Model | Approximate Cost per Call | Speed | Best For |
|-------|--------------------------|-------|----------|
| Haiku | ~$0.003-0.005 | 2-5 sec | Scoring, classification, simple generation |
| Sonnet | ~$0.015-0.025 | 5-15 sec | Creative writing, nuanced analysis |
| Opus | ~$0.060-0.100 | 15-45 sec | Complex reasoning, multi-step analysis |

*Estimates based on typical prompt sizes (2-4K tokens input, 200-500 tokens output). Actual costs vary.*

### Mixed Model Strategy

The key insight: not every skill needs the best model. Use the cheapest model that produces acceptable quality.

| Skill Type | Recommended Model | Reasoning |
|------------|-------------------|-----------|
| ICP Scoring | Haiku | Structured scoring against criteria — Haiku handles this well |
| Angle Selection | Haiku | Decision logic, not creative writing |
| Email Generation | Sonnet | Creative writing benefits from the quality jump |
| LinkedIn Notes | Haiku | Short-form (300 chars), Haiku is sufficient |
| Meeting Prep | Sonnet | Synthesis and judgment calls need quality |
| Campaign Brief | Sonnet | Strategic thinking, multiple considerations |
| Quality Gate | Haiku | Pattern matching against rules — fast and cheap |

### Per-Row Cost for a 4-Skill Chain

```
ICP Score (Haiku):      $0.004
Angle Select (Haiku):   $0.004
Email Gen (Sonnet):     $0.020
Quality Gate (Haiku):   $0.003
──────────────────────────────
Total per row:          ~$0.031
```

### Batch Economics

| Batch Size | 4-Skill Chain Cost | Time (Haiku-heavy) | Time (Sonnet-heavy) |
|------------|-------------------|---------------------|---------------------|
| 100 rows | ~$3 | ~15 min | ~30 min |
| 500 rows | ~$15 | ~75 min | ~2.5 hours |
| 1,000 rows | ~$31 | ~2.5 hours | ~5 hours |
| 5,000 rows | ~$155 | ~12 hours | ~25 hours |

### Claude Code Max Subscription Model

With Claude Code Max ($100-200/month, depending on plan):
- **Flat rate** — no per-token billing, no surprise costs
- **Rate limits** — you'll hit rate limits before you hit cost limits
- **Predictable** — budget is fixed regardless of volume

**Rate limit considerations:**
- Haiku: ~50-100 requests/minute (generous)
- Sonnet: ~20-40 requests/minute (moderate)
- Opus: ~5-10 requests/minute (tight)

For a 1,000-row batch on Sonnet, you'll spread across ~30-60 minutes naturally due to processing time. Rate limits rarely bite unless you're running multiple campaigns simultaneously.

### Cost Comparison: AI vs. Traditional

| Approach | Cost per 1,000 Emails | Quality | Speed |
|----------|----------------------|---------|-------|
| Junior copywriter | $2,000-5,000 | Variable | 2-4 weeks |
| Freelance specialist | $5,000-10,000 | High | 1-2 weeks |
| Generic AI (no context) | ~$5-10 | Low (template-y) | Minutes |
| **Webhook OS (with context)** | **~$15-30** | **High (calibrated)** | **2-5 hours** |

The Webhook OS hits the sweet spot: near-human quality at AI cost and speed.

### What Would Actually Get Expensive

1. **Running Opus on everything** — 6-20x more expensive than Haiku. Only use for complex reasoning tasks.
2. **Huge context windows** — if your knowledge base + client context exceeds 10K tokens, costs scale with input size. Keep context files focused and concise.
3. **Re-running without caching** — same prospect, same data, same skill = same output. Cache results to avoid paying twice.
4. **No filtering before creative skills** — running Sonnet on 1,000 rows when only 300 are ICP-fit wastes 70% of your creative budget. Always score first, generate second.

**How to keep costs down:**
- Score on Haiku → filter → generate on Sonnet
- Keep knowledge files under 2K tokens each
- Cache results for rows that haven't changed
- Use pipeline filters to short-circuit low-fit prospects

---

## Part 9: Knowledge Base — What's Available

### Existing Knowledge in the Webhook OS Repo

| File | Domain | What It Contains |
|------|--------|-----------------|
| `knowledge_base/frameworks/josh-braun-pvc.md` | Methodology | PVC framework — Permission, Value, CTA. Anti-patterns. Evidence from 50+ campaigns |
| `knowledge_base/voice/writing-style.md` | Methodology | Voice characteristics, patterns to use/avoid, tone by context |
| `knowledge_base/industries/saas-b2b.md` | Business | SaaS B2B pain points, buyer personas by title, resonant/banned language, signals |
| `clients/_template.md` | — | Template for new client context files (company, value prop, ICP, tone, campaign notes) |

### Knowledge Graph System

The `_system/knowledge_graph/` directory defines how knowledge nodes relate:

- **taxonomy.yaml**: Blessed domains (business, methodology, technical, emergent), node types (concept, pattern, case-study, framework), status values (emergent → validated → canonical)
- **ontology.yaml**: Relationship types (enables, supports, implements, informs) with linking requirements

Every knowledge file uses frontmatter metadata:
```yaml
---
name: JOSH_BRAUN_PVC_FRAMEWORK
domain: methodology
node_type: framework
status: validated
tags: [methodology, cold-email, outbound]
topics: [email-writing, personalization, cold-outreach]
related_concepts: ["[[writing-style]]", "[[b2b-outbound-patterns]]"]
---
```

### GTM Knowledge Available for Porting

The Mangu GTM workspace (`gtm-workspace/operations/knowledge/`) contains 28 knowledge files across 5 domains that can be ported into the Webhook OS:

#### Outbound Domain (5 files)
| File | What It Contains | Useful For Skills |
|------|-----------------|-------------------|
| Cold Email Sequencing | 5-touch and 7-touch sequence structures, timing rules, personalization layers | follow-up sequences, campaign-brief |
| Subject Line Patterns | 5 proven formulas (Question, Pain-Agitation, Curiosity Gap, Social Proof, Direct Value) | email-gen, follow-up |
| LinkedIn Connection Requests | 5 connection patterns with acceptance rate expectations | linkedin-note |
| Buying Signals Taxonomy | Intent, technographic, hiring, funding signals with decay rates | angle-selector, icp-scorer |
| Intent Data Sources | Bombora, G2, 6sense, ZoomInfo specs and integration notes | icp-scorer |

#### Enrichment Domain (7 files)
| File | What It Contains | Useful For Skills |
|------|-----------------|-------------------|
| Waterfall Design | Provider stacking patterns, cheapest-first logic, coverage projections | campaign-brief |
| Credit Optimization | Cost traps and fixes for Clay enrichment credits | campaign-brief |
| Hub-Spoke Architecture | Multi-table patterns for efficient enrichment | system design |
| Claygent Prompting | 5-part prompt framework (Role, Task, Process, Fallback, Output) | skill writing |
| Apollo | 270M+ contacts, email coverage 50-60%, waterfall position 1 | enrichment context |
| Clearbit | Enterprise company data, HubSpot integration | enrichment context |
| People Data Labs | Job history + education differentiators | enrichment context |

#### RevOps Domain (7 files)
| File | What It Contains | Useful For Skills |
|------|-----------------|-------------------|
| Pipeline Stage Definitions | 7-stage funnel with conversion benchmarks (1-3% end-to-end) | campaign-brief, icp-scorer |
| Lead Scoring | 4-category model (demographic, firmographic, behavioral, intent) | icp-scorer |
| CRM Selection Framework | HubSpot vs Salesforce decision matrix | client onboarding |
| Clay-HubSpot Integration | Import/push patterns, upsert logic | pipeline skills |
| Clay-Salesforce Integration | SOQL queries, 3 import methods | pipeline skills |
| Zapier Patterns | Event-driven automation for GTM | workflow design |

#### Content Domain (4 files)
| File | What It Contains | Useful For Skills |
|------|-----------------|-------------------|
| Social Playbook | LinkedIn cadence (3-5 posts/week), 5 content types | linkedin-note |
| Thought Leadership | Authority Triangle framework, topic selection scoring | campaign-brief |
| Content Pillars | Pillar/cluster SEO architecture | content skills |
| Context Engineering | Methodology for structuring company context into files | skill extraction |

#### Analytics Domain (4 files)
| File | What It Contains | Useful For Skills |
|------|-----------------|-------------------|
| Email Benchmarks | Open rates (15-25%), reply rates (2-5%), meeting book rates (0.5-2%) | quality-gate thresholds |
| LinkedIn Benchmarks | Connection acceptance (20-30%), by persona level | linkedin-note optimization |
| KPI Frameworks | Marketing, sales, and CS metrics | campaign-brief |
| Reporting Cadence | Daily/weekly/monthly/quarterly review structures | system design |

### How to Add New Knowledge Files

1. Create the file in the appropriate directory:
   - `knowledge_base/frameworks/` for methodologies
   - `knowledge_base/voice/` for writing/tone guides
   - `knowledge_base/industries/` for industry context (auto-loaded by `data.industry`)
2. Add frontmatter metadata (name, domain, node_type, status, tags, topics, related_concepts)
3. Reference it in your skill's "Context Files to Load" section
4. Industry files auto-load — no skill changes needed when `data.industry` matches the filename

### Adding Client Context

1. Copy `clients/_template.md` to `clients/[slug].md`
2. Fill in: Company info, Value Proposition, Target ICP, Tone Preferences, Campaign Notes
3. Skills reference via `clients/{{client_slug}}.md` — Clay sends the slug in `data.client_slug`

---

## Part 10: Reference

### Email-Gen Skill (Complete Template)

The `email-gen` skill is the reference implementation. See `skills/email-gen/skill.md` for the full file. Key sections:

- **Role:** Senior B2B copywriter, Josh Braun PVC framework
- **Context Files:** PVC framework + writing style + client context (via `{{client_slug}}`)
- **Output Format:** 5 fields — `email_subject`, `email_body`, `personalization_hook`, `framework_notes`, `confidence_score`
- **Rules:** 8 rules covering subject lines, openers, banned phrases, word count, CTA style, tone matching, confidence thresholds
- **Examples:** 2 complete input/output pairs (high-data at 0.92, low-data at 0.45)

### Client Context Template

```markdown
# {{Client Name}}

## Company
- **Domain:** —
- **Industry:** —
- **Size:** —
- **Stage:** —

## Value Proposition
What does this client sell? One sentence.

## Target ICP
Who are they trying to reach? Title, company size, industry.

## Tone Preferences
- **Formality:** casual / professional / formal
- **Approach:** direct / consultative / educational
- **Things to avoid:** —

## Campaign Notes
Any active campaign context, angles, or themes.
```

### New Skill Template

```markdown
# [Skill Name] — [Category]

## Role
You are a [specific role]. You [key capability]. You [key constraint].

## Context Files to Load
- knowledge_base/frameworks/[relevant-framework].md
- knowledge_base/voice/writing-style.md
- clients/{{client_slug}}.md

## Output Format
Return ONLY valid JSON. No markdown, no explanation.
Exact keys required:
{
  "field_1": "type and constraints",
  "field_2": "type and constraints",
  "confidence_score": "number 0.0-1.0"
}

## Data Fields (flexible — use what's available)
Ideal fields: [list expected fields from Clay]

If a field is missing, adjust confidence_score:
- All key fields present: 0.8-1.0
- Partial data: 0.5-0.7
- Minimal data: 0.3-0.5

## Rules
1. [Rule about output format]
2. [Rule about content quality]
3. [Rule about what to never do]
4. [Rule about handling edge cases]

## Examples

### Input:
{ [high-data example] }

### Output:
{ [expected output with high confidence] }

### Input:
{ [low-data example] }

### Output:
{ [expected output with low confidence] }
```

### API Quick Reference

```bash
# Health check
curl https://<domain>/health

# List skills
curl https://<domain>/skills

# Test echo (debug request format)
curl -X POST https://<domain>/test-echo \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Run a skill
curl -X POST https://<domain>/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "skill": "email-gen",
    "data": {
      "first_name": "Sarah",
      "company_name": "Acme",
      "title": "VP Sales",
      "industry": "SaaS",
      "client_slug": "your-client"
    },
    "model": "haiku"
  }'

# Run with campaign instructions
curl -X POST https://<domain>/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "skill": "email-gen",
    "data": { ... },
    "instructions": "Focus on the scaling challenge post-raise. Mention SDR productivity.",
    "model": "sonnet"
  }'
```

### Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `spawn claude ENOENT` | Claude CLI not in PATH | Start with: `PATH="./node_modules/.bin:$PATH" node index.js` |
| `EADDRINUSE port 3000` | Port already in use | `pkill -f node; sleep 1; node index.js` |
| `Credit balance too low` | Claude session expired | Re-login: `./node_modules/.bin/claude login` |
| Clay gets 400 HTML error | Wrong URL or missing Content-Type | Use dev URL (not deployment). Add `Content-Type: application/json` header |
| `Skill not found` | Missing skill.md file | Verify `skills/[name]/skill.md` exists on Replit |
| Empty response from Claude | CLI error | Check Replit console for stderr output. May need re-login |
| Server stops when tab closes | Replit dev mode limitation | Keep tab open or use "Always On" (paid) |
| JSON parse error on response | Claude returned markdown-wrapped JSON | Server strips markdown fences automatically. If persisting, check skill file's "Return ONLY valid JSON" instruction |
| Slow responses (>30 sec) | Using Opus or large context | Switch to Haiku/Sonnet. Trim knowledge files. Check prompt size |
| Same output for different rows | Context not varying | Verify `data` fields are being passed correctly in Clay's HTTP Action |

### Learning Resources

#### Webhooks
- [What Are Webhooks — Hookdeck](https://hookdeck.com/webhooks/guides/what-are-webhooks-how-they-work) — Best written explainer (10 min)
- [Webhooks for Beginners — freeCodeCamp](https://www.freecodecamp.org/news/the-ultimate-webhooks-course-for-beginners/) — Free video course (2-3 hours)

#### Clay-Specific
- [Clay Webhook Integration Guide](https://www.clay.com/university/guide/webhook-integration-guide) — Official docs
- [Using Clay as an API](https://www.clay.com/university/guide/using-clay-as-an-api) — HTTP Actions reference
- [Clay Webhooks Tutorial (Video)](https://www.youtube.com/watch?v=EWmK1NZPdpc) — Visual walkthrough

#### Express.js
- [Building a Webhook Listener with Node.js](https://dev.to/lucasbrdt268/building-a-webhook-listener-with-nodejs-step-by-step-guide-3ai5) — Beginner step-by-step (15 min)

#### Claude Code CLI
- [Claude Code CLI Reference](https://docs.anthropic.com/en/docs/claude-code/cli-usage) — Official `--print` docs
- [Claude Code Cheatsheet](https://shipyard.build/blog/claude-code-cheat-sheet/) — Practical scripting examples

#### Replit Hosting
- [How Replit Deployments Work](https://rpltbldrs.com/p/how-do-replit-deployments-work) — Dev vs deployed mode explained

---

## Appendix: Glossary

| Term | What It Means |
|------|-------------|
| **Skill** | A markdown file defining a specific AI task — role, context refs, rules, output schema, examples |
| **Knowledge base** | Reusable context files (frameworks, voice guides, industry intel) injected into prompts |
| **Client context** | Per-client file with value prop, ICP, tone, campaign notes — loaded via `{{client_slug}}` |
| **Pipeline** | A sequence of skills that run in order, each feeding the next |
| **Confidence score** | 0.0-1.0 rating reflecting data quality and personalization potential |
| **PVC** | Permission-Value-CTA — Josh Braun's cold email framework |
| **ICP** | Ideal Customer Profile — the type of company/person you're targeting |
| **Signal** | An external event (funding, hiring, tech change) that creates a reason to reach out |
| **Angle** | The specific approach/theme for a message, derived from a signal |
| **Context mesh** | Dynamic context assembly combining static knowledge + live data from multiple sources |
| **Quality gate** | An AI copy editor that checks output against rules before returning to Clay |
| **Dedup brain** | System that prevents the same company from receiving the same angle twice |

---

*Last updated: 2026-03-05*
*Project: [github.com/ferm-the-kiln/clay-webhook-os](https://github.com/ferm-the-kiln/clay-webhook-os)*
