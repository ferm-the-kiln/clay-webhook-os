---
name: qualify-companies
description: Qualify companies for Hologram IoT cellular fit. Self-contained — no repo needed. Takes a CSV file path as input.
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
**Self-contained** — runs in any Claude Code session. No repo clone needed.

## Setup Check (run first)

<step>
Before anything else, verify the environment is ready. Run these checks:

1. **Python 3.11+**: Run `python3 --version` (or `python3.11 --version`). If missing, tell the user to install Python 3.11+.
2. **pip packages**: Run `python3 -c "import httpx; print('httpx OK')"` and `python3 -c "from parallel import AsyncParallel; print('parallel OK')"`. If either fails, run `pip3 install httpx parallel-sdk`.
3. **API keys**: Check for these environment variables:
   - `PARALLEL_API_KEY` — run `echo $PARALLEL_API_KEY`. If empty, tell the user: "Set your Parallel.ai API key: `export PARALLEL_API_KEY=your_key_here`". Get one at https://parallel.ai
   - `DEEPLINE_API_KEY` — run `echo $DEEPLINE_API_KEY`. If empty, tell the user: "Set your DeepLine API key: `export DEEPLINE_API_KEY=your_key_here`". Get one free at https://deepline.com

4. **Working directory**: Create a `data/` folder in the current directory if it doesn't exist: `mkdir -p data`

If ANY check fails, stop and guide the user through fixing it. Do NOT proceed until all checks pass.

Print: "Environment ready. Python ✓ | httpx ✓ | parallel-sdk ✓ | PARALLEL_API_KEY ✓ | DEEPLINE_API_KEY ✓"
</step>

## Pipeline

1. **Load CSV** — expects columns: `name` (or `company_name` or `Company Name`) and `domain` (or `company_domain` or `Company Domain`)
2. **Enrich** — for each company, run in parallel:
   - Parallel Search (2 AI-powered web searches via Parallel.ai)
   - Apollo company profile via DeepLine (LinkedIn description, industry, keywords — free)
   - Domain keyword analysis (instant, no API)
3. **Qualify** — Claude Code (this session) reads the enrichment data and qualifies each company
4. **Output** — writes results to `data/qualification_results.csv` and prints summary

## Process

<step>
Read the CSV file provided as argument. Parse it and extract company name + domain for each row. Print how many companies were found. If no CSV path was provided, ask the user for one.
</step>

<step>
Write this COMPLETE enrichment script to `/tmp/qualify_enrich.py`, then run it.

```python
"""Self-contained enrichment script for company qualification."""
import asyncio, csv, json, os, re, sys, time
from dataclasses import dataclass, field

import httpx

# ── Config ──────────────────────────────────────────────────────────
PARALLEL_API_KEY = os.environ.get("PARALLEL_API_KEY", "")
DEEPLINE_API_KEY = os.environ.get("DEEPLINE_API_KEY", "")
DEEPLINE_URL = "https://code.deepline.com"

# ── Domain Analyzer (no API calls) ─────────────────────────────────
IOT_KEYWORDS = {
    "gps": "GPS / Fleet Tracking", "fleet": "GPS / Fleet Tracking",
    "tracker": "GPS / Fleet Tracking", "tracking": "GPS / Fleet Tracking",
    "telematics": "GPS / Fleet Tracking", "obd": "GPS / Fleet Tracking",
    "dashcam": "GPS / Fleet Tracking", "asset track": "GPS / Fleet Tracking",
    "scooter": "Micromobility", "e-bike": "Micromobility",
    "ebike": "Micromobility", "micromobility": "Micromobility",
    "shared mobility": "Micromobility",
    "farm": "Agriculture / Livestock", "agri": "Agriculture / Livestock",
    "livestock": "Agriculture / Livestock", "irrigation": "Agriculture / Livestock",
    "precision agriculture": "Agriculture / Livestock",
    "cattle": "Agriculture / Livestock", "herd": "Agriculture / Livestock",
    "smart building": "Smart Buildings", "building automation": "Smart Buildings",
    "hvac": "Smart Buildings", "facility monitoring": "Smart Buildings",
    "sensor": "Industrial Monitoring", "telemetry": "Industrial Monitoring",
    "industrial iot": "Industrial Monitoring",
    "predictive maintenance": "Industrial Monitoring",
    "gas meter": "Industrial Monitoring", "thermal imaging": "Industrial Monitoring",
    "robot": "Robotics / Autonomous", "drone": "Robotics / Autonomous",
    "uav": "Robotics / Autonomous", "auv": "Robotics / Autonomous",
    "autonomous": "Robotics / Autonomous", "unmanned": "Robotics / Autonomous",
    "medical device": "Medical Devices", "patient monitoring": "Medical Devices",
    "cold chain": "Medical Devices",
    "container track": "Supply Chain", "shipment monitor": "Supply Chain",
    "cargo monitor": "Supply Chain",
    "connected vehicle": "Connected Vehicles", "heavy equipment": "Connected Vehicles",
    "iot gateway": "IoT Platform", "edge device": "IoT Platform",
    "iot platform": "IoT Platform",
    "sim card": "", "sim management": "", "lte-m": "", "cat-m1": "",
    "nb-iot": "", "cellular modem": "", "cellular connect": "", "esim": "", "m2m": "",
}

EXCLUSION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bbank(ing)?\b", r"\bfinancial\s+services?\b", r"\binsurance\b",
    r"\bfashion\b", r"\bapparel\b", r"\bfood\s*&?\s*beverage\b", r"\bcpg\b",
    r"\bhr\s+(software|saas|payroll)\b", r"\bpayroll\b",
    r"\bmedia\s+(company|publish|group)\b", r"\bpublishing\b",
    r"\blegal\s+service\b", r"\blaw\s+firm\b", r"\bholding\s+compan",
    r"\bprivate\s+equity\b", r"\bventure\s+capital\b", r"\b(pe|vc)\s+firm\b",
    r"\bdistiller", r"\balcohol\b", r"\bhospitality\b",
    r"\bhotel\s+(chain|group|management)\b", r"\bconsulting\s+(firm|group|compan)\b",
]]

def analyze_domain(name, domain=""):
    text = f"{name} {domain}".lower()
    for p in EXCLUSION_PATTERNS:
        if p.search(text):
            return {"keyword_matches": {}, "confidence_boost": 0.0,
                    "suggested_archetype": "", "is_hard_exclusion": True,
                    "reasoning": f"Hard exclusion: {p.pattern}"}
    matches = {k: v for k, v in IOT_KEYWORDS.items() if k in text}
    boost = 0.3 if len(matches) >= 3 else 0.2 if len(matches) == 2 else 0.1 if matches else 0.0
    archetypes = [a for a in matches.values() if a]
    archetype = max(set(archetypes), key=archetypes.count) if archetypes else ""
    return {"keyword_matches": matches, "confidence_boost": boost,
            "suggested_archetype": archetype, "is_hard_exclusion": False,
            "reasoning": f"Found {len(matches)} IoT keyword(s)" if matches else "No IoT keywords"}


# ── Parallel Search ─────────────────────────────────────────────────
async def fetch_parallel(name, domain, key):
    if not key:
        return {}
    try:
        from parallel import AsyncParallel
        client = AsyncParallel(api_key=key)
        product_coro = client.beta.search(
            objective=f"Find what products {name} ({domain}) builds or manufactures. Look for physical hardware devices, sensors, trackers, gateways, or equipment.",
            search_queries=[
                f"site:{domain} products OR hardware OR device" if domain else f'"{name}" products hardware',
                f'"{name}" manufactures OR builds OR deploys hardware device sensor tracker',
            ],
            mode="fast", max_results=8, excerpts={"max_chars_per_result": 500},
        )
        connectivity_coro = client.beta.search(
            objective=f"Find evidence that {name} uses cellular IoT connectivity or deploys connected devices — SIM cards, LTE-M, CAT-M1, NB-IoT, telematics, GPS tracking, fleet management.",
            search_queries=[
                f'"{name}" "GPS tracker" OR "fleet tracking" OR "IoT device" OR "SIM card" OR telematics OR "connected devices"',
                f'"{name}" "LTE-M" OR "CAT-M1" OR "NB-IoT" OR "cellular" OR deploys OR "fleet management"',
            ],
            mode="fast", max_results=8, excerpts={"max_chars_per_result": 500},
        )
        prod_resp, conn_resp = await asyncio.gather(product_coro, connectivity_coro, return_exceptions=True)

        def parse(resp):
            if isinstance(resp, Exception): return []
            return [{"title": getattr(r,"title",""), "url": getattr(r,"url",""),
                     "snippet": " ".join(getattr(r,"excerpts",[]) or [])[:500]}
                    for r in (resp.results if resp else [])]

        prod, conn = parse(prod_resp), parse(conn_resp)
        parts = []
        if prod:
            parts.append("--- PRODUCT SEARCH ---")
            parts.extend(f"[{r['title']}] {r['snippet']}" for r in prod if r.get("snippet"))
        if conn:
            parts.append("--- CONNECTIVITY SEARCH ---")
            parts.extend(f"[{r['title']}] {r['snippet']}" for r in conn if r.get("snippet"))
        return {"product_search": prod, "connectivity_search": conn, "all_snippets": "\n".join(parts)[:4000]}
    except Exception as e:
        print(f"    [warn] Parallel failed for {name}: {e}", file=sys.stderr)
        return {}


# ── Apollo / DeepLine ───────────────────────────────────────────────
async def fetch_apollo(domain, key):
    if not domain or not key:
        return {}
    try:
        async with httpx.AsyncClient(
            base_url=DEEPLINE_URL, headers={"Authorization": f"Bearer {key}",
            "Content-Type": "application/json"}, timeout=30,
        ) as client:
            resp = await client.post("/api/v2/integrations/execute", json={
                "provider": "apollo", "operation": "apollo_enrich_company",
                "payload": {"domain": domain},
            })
            org = resp.json().get("result", {}).get("data", {}).get("organization", {})
            if not org: return {}
            return {"description": org.get("short_description","") or "",
                    "industry": org.get("industry","") or "",
                    "keywords": (org.get("keywords") or [])[:15],
                    "employees": org.get("estimated_num_employees"),
                    "name": org.get("name",""), "linkedin_url": org.get("linkedin_url","")}
    except Exception as e:
        print(f"    [warn] Apollo failed for {domain}: {e}", file=sys.stderr)
        return {}


# ── Enrichment orchestrator ─────────────────────────────────────────
async def enrich(company, sem):
    name, domain = company["name"], company["domain"]
    async with sem:
        start = time.monotonic()
        da = analyze_domain(name, domain)
        tasks = []
        if PARALLEL_API_KEY: tasks.append(fetch_parallel(name, domain, PARALLEL_API_KEY))
        if DEEPLINE_API_KEY and domain: tasks.append(fetch_apollo(domain, DEEPLINE_API_KEY))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        par, apo = {}, {}
        idx = 0
        if PARALLEL_API_KEY:
            par = results[idx] if not isinstance(results[idx], Exception) else {}
            idx += 1
        if DEEPLINE_API_KEY and domain:
            apo = results[idx] if not isinstance(results[idx], Exception) else {}
        return {
            "id": company["id"], "company_name": name, "company_domain": domain,
            "all_snippets": par.get("all_snippets",""), "parallel": par,
            "apollo_desc": apo.get("description","") or "",
            "apollo_industry": apo.get("industry","") or "",
            "apollo_keywords": apo.get("keywords",[]) or [],
            "domain_analysis": da,
            "duration_ms": int((time.monotonic()-start)*1000),
        }


# ── CSV loader ──────────────────────────────────────────────────────
def load_csv(path):
    companies = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            name = row.get("name") or row.get("company_name") or row.get("Name") or row.get("Company Name") or row.get("Company") or ""
            domain = row.get("domain") or row.get("company_domain") or row.get("Domain") or row.get("Company Domain") or row.get("Website") or row.get("website") or ""
            domain = domain.replace("https://","").replace("http://","").replace("www.","").rstrip("/")
            if name.strip() or domain.strip():
                companies.append({"id": i+1, "name": name.strip(), "domain": domain.strip()})
    return companies


# ── Main ────────────────────────────────────────────────────────────
async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    companies = load_csv(args.csv_path)
    if args.limit: companies = companies[:args.limit]
    total = len(companies)

    print(f"Hologram Company Enrichment")
    print(f"{'='*60}")
    print(f"  Companies: {total}")
    print(f"  Parallel: {'...'+PARALLEL_API_KEY[-4:] if PARALLEL_API_KEY else 'NOT SET'}")
    print(f"  Apollo: {'...'+DEEPLINE_API_KEY[-4:] if DEEPLINE_API_KEY else 'NOT SET'}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Est. cost: ~${total * 0.01:.2f} (Parallel) + $0.00 (Apollo)")
    print()

    sem = asyncio.Semaphore(args.concurrency)
    results = []
    start_time = time.monotonic()

    coros = [enrich(c, sem) for c in companies]
    for coro in asyncio.as_completed(coros):
        r = await coro
        results.append(r)
        i = len(results)
        p = "P" if r["all_snippets"] else "-"
        a = "A" if r["apollo_desc"] else "-"
        d = "D" if r["domain_analysis"]["suggested_archetype"] else "-"
        print(f"  [{i:3d}/{total}] [{p}{a}{d}] {r['company_name']:40s} {r['duration_ms']}ms")

    results.sort(key=lambda r: r["id"])
    elapsed = (time.monotonic()-start_time)
    wp = sum(1 for r in results if r["all_snippets"])
    wa = sum(1 for r in results if r["apollo_desc"])
    print(f"\n{'='*60}")
    print(f"DONE: {total} companies in {elapsed:.1f}s")
    print(f"  Parallel: {wp}/{total} ({wp/total*100:.0f}%) | Apollo: {wa}/{total} ({wa/total*100:.0f}%)")

    out = "data/qualification_enrichment.json"
    with open(out, "w") as f:
        json.dump({"total": total, "results": results}, f, indent=2)
    print(f"  Saved: {out}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run with: `python3 /tmp/qualify_enrich.py <csv_path> --concurrency 3`

Wait for it to complete. It will save enrichment data to `data/qualification_enrichment.json`.
</step>

<step>
Load enrichment results from `data/qualification_enrichment.json`. Build batches of 15 companies each with: id, name, domain, parallel search snippets, apollo description/industry/keywords, domain analysis archetype.

Write batches to `data/batch_XX.json`. Do NOT include any CRM data — qualify based on public research only.
</step>

<step>
Qualify all companies by reading each batch and producing Y/N verdicts. Use 4 parallel Agent subprocesses to speed this up.

Each agent gets this qualification prompt:

---

You are a B2B qualification analyst for Hologram (hologram.io) — a global IoT cellular connectivity platform that sells SIM cards to companies deploying connected hardware.

**Y = company would benefit from Hologram's cellular SIM management. Three patterns:**

### Pattern A — Device Builders (60% of customers)
Companies building physical hardware deployed outdoors, in vehicles, or remote sites:
- GPS/Fleet Tracking (~35%): "GPS tracker", "fleet tracking", "telematics", "asset tracker"
- Micromobility (~10%): "e-scooter", "e-bike", "shared mobility"
- Agriculture (~10%): "livestock tracking", "farm sensor", "precision agriculture"
- Industrial Monitoring (~8%): "industrial sensor", "gas meter", "telemetry"
- Robotics/Autonomous (~8%): "drone", "robot", "UAV" — AUTO-QUALIFY
- Medical Devices (~3%): "remote patient monitoring", "wearable biosensor"
- Supply Chain (~5%): "container tracking", "cargo monitoring", "cold chain"
- Connected Vehicles (~5%): Manufacturers adding connectivity to equipment
- EV Charging: Companies that MANUFACTURE EV chargers = Y

### Pattern B — Indoor IoT (15% of customers)
Sensors/hardware in buildings needing cellular (WiFi unreliable):
- Building automation, occupancy sensors, energy management
- Vending machines, smart kiosks, POS terminals

### Pattern C — Software + Hardware Bundlers (10% of customers)
SaaS companies that ALSO ship physical devices. Evidence of BOTH platform AND hardware = Y.

### BLE/RFID Pattern
Bluetooth/RFID devices deployed in field → need cellular gateway = Y

**N = pure software, consulting, advocacy/associations, media, carriers/competitors, engineering firms, component suppliers (cables, connectors), installers that don't build their own hardware.**

When genuinely uncertain, lean Y — false negatives are worse than false positives.

---

Each agent writes verdicts to `/tmp/qualify_batch_XX.json` as JSON array:
```json
[{"id": 1, "name": "...", "domain": "...", "qualified": "Y", "archetype": "EV Charging", "confidence": 0.85, "reasoning": "..."}]
```
</step>

<step>
Combine all verdict files. Write a final CSV to `data/qualification_results.csv` with columns:
- Company Name, Domain, Qualified (Y/N), Archetype, Confidence, Reasoning

Also print a summary:
- Total companies, Y count, N count
- Archetype distribution for Y verdicts
- List of top N verdicts with reasoning

Save JSON version to `data/qualification_results.json` as well.
</step>

## Cost

- **Parallel Search**: ~$0.01 per company (2 AI searches)
- **Apollo/DeepLine**: Free
- **Domain Analysis**: Free (no API, keyword matching)
- **Example**: 200 companies ≈ $2.00 total

## Important Rules

- NEVER use `claude --print` or start any server
- Process qualification locally in this Claude Code session using Agent subprocesses
- Use `python3` for Python (detect the right binary: `python3`, `python3.11`, or `python`)
- Save all intermediate data to `data/` directory
- If no CSV path is provided, prompt the user for one
