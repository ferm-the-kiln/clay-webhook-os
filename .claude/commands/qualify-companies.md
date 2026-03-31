---
name: qualify-companies
description: Qualify companies for Hologram IoT cellular fit using Parallel Search + Apollo enrichment. Takes a CSV file path as input.
argument-hint: "<csv-file-path>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - Agent
---

# Company Qualifier — IoT Cellular Connectivity Fit

Qualify a batch of companies for Hologram (hologram.io) using public research data only.

## Pipeline

1. **Load CSV** — expects columns: `name` (or `company_name`) and `domain` (or `company_domain`)
2. **Enrich** — for each company, run in parallel:
   - Parallel Search (2 AI-powered web searches via Parallel.ai)
   - Apollo company profile via DeepLine (LinkedIn description, industry, keywords — free)
   - Domain keyword analysis (instant, no API)
3. **Qualify** — Claude Code (this session) reads the enrichment data and qualifies each company using the 3-pattern framework:
   - **Pattern A: Device Builders** — builds hardware deployed outdoors/mobile/remote (GPS trackers, sensors, drones, medical devices)
   - **Pattern B: Indoor IoT** — deploys sensors/hardware inside buildings (occupancy, energy, vending, kiosks) that still need cellular
   - **Pattern C: Software + Hardware Bundlers** — SaaS company that also ships physical devices
4. **Output** — writes results to `data/qualification_results.json` and prints summary

## Process

<step>
Read the CSV file provided as argument. Parse it and extract company name + domain for each row. Print how many companies were found.
</step>

<step>
Run the enrichment script for all companies. Use this Python script pattern:

```python
import asyncio, json, sys, time, httpx, re
sys.path.insert(0, '.')
from app.config import settings
from app.core.research_fetcher import fetch_parallel_qualification, fetch_apollo_company
from app.core.domain_analyzer import analyze_domain_signals

# For each company: run Parallel Search + Apollo + Domain Analysis in parallel
# Save enrichment results to data/qualification_enrichment.json
```

Run with: `/opt/homebrew/bin/python3.11 scripts/run_enrichment.py <csv_path>`

If the enrichment script doesn't exist, create it first. Use concurrency 3-5 for Parallel, 5 for Apollo.
</step>

<step>
Load the enrichment results. Build batches of 15 companies each with: id, name, domain, parallel search snippets, apollo description/industry/keywords, domain analysis archetype.

Write batches to `data/cw_batch_XX.json`. Do NOT include any CRM data (descriptions, notes) — qualify based on public research only.
</step>

<step>
Qualify all companies by reading each batch and producing Y/N verdicts. Use 4 parallel Agent subprocesses to speed this up.

Each agent gets this qualification prompt:

**Y = company would benefit from Hologram's cellular SIM management. Three patterns:**
- Pattern A (Device Builders): Hardware deployed outdoors, in vehicles, remote sites
- Pattern B (Indoor IoT): Sensors/hardware in buildings — cellular because WiFi unreliable for IoT
- Pattern C (Software + Hardware Bundlers): "Platform" companies that also ship devices

**N = pure software, chip makers, carriers, no hardware evidence, wrong search results.**

When uncertain, lean Y — false negatives are worse than false positives.

Each agent writes verdicts to `/tmp/qualify_batch_XX.json` as JSON array.
</step>

<step>
Combine all verdict files. Compute and display:
- Total companies, Y count, N count, accuracy percentage
- Archetype distribution
- List of N verdicts (false negatives if testing against CW data)
- Save combined results to `data/qualification_results.json`
</step>

## Key Configuration

- **Parallel API key**: `settings.parallel_api_key` (from .env)
- **DeepLine API key**: `settings.deepline_api_key` (for Apollo, free)
- **Python**: `/opt/homebrew/bin/python3.11`
- **Cost**: ~$0.010 per company (Parallel Search only, Apollo is free)

## Important Rules

- NEVER use `claude --print` or start the webhook server
- Process qualification locally in this Claude Code session using Agent subprocesses
- Always use `/opt/homebrew/bin/python3.11` for Python
- Save all intermediate data to `data/` directory
- If no CSV path is provided, prompt the user for one
