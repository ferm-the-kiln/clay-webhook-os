"""Run company-qualifier logic on all 251 CW companies using pre-fetched waterfall data.

Implements the skill's qualification criteria as code — no API calls, no claude --print.
Processes all companies instantly using keyword/pattern matching + archetype detection.

Usage:
    python scripts/qualification_benchmark.py [--limit N] [--verbose]
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.domain_analyzer import IOT_KEYWORDS, EXCLUSION_PATTERNS, analyze_domain_signals

CW_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_companies.json"
WATERFALL_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_waterfall_results.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_qualification_results.json"

# ── Strong signal keywords (from skill.md) ────────────────────────

HARDWARE_KEYWORDS = [
    "gps tracker", "fleet tracking", "asset tracker", "telematics",
    "sensor", "gateway", "modem", "hardware", "device", "tracker",
    "e-scooter", "e-bike", "drone", "uav", "robot", "autonomous",
    "smart building", "building automation", "hvac",
    "livestock", "farm sensor", "precision agriculture", "irrigation",
    "medical device", "patient monitoring", "cold chain",
    "container tracking", "shipment monitor", "cargo",
    "industrial sensor", "thermal imaging", "gas meter", "telemetry",
    "iot gateway", "edge device", "connected device",
    "camera", "dashcam", "wearable", "beacon", "tag",
    "firmware", "embedded", "pcb", "antenna",
    "manufactur", "deploy", "fleet",
]

CELLULAR_KEYWORDS = [
    "sim card", "sim management", "lte", "lte-m", "cat-m1", "nb-iot",
    "cellular", "esim", "m2m", "4g", "5g", "2g", "3g",
    "carrier", "data plan", "connectivity", "wireless",
    "at command", "modem", "gprs",
]

STRONG_N_KEYWORDS = [
    "software company", "saas platform", "consulting firm",
    "marketing agency", "law firm", "accounting",
    "staffing", "recruitment", "real estate",
    "restaurant", "food delivery", "retail store",
    "ecommerce", "online store", "marketplace",
    "media company", "publishing", "news",
    "investment fund", "venture capital", "private equity",
    "insurance company", "bank", "financial services",
]

ARCHETYPE_PATTERNS = {
    "GPS / Fleet Tracking": [
        r"gps.?track", r"fleet.?track", r"asset.?track", r"telematics",
        r"vehicle.?track", r"obd", r"dashcam", r"location.?track",
    ],
    "Micromobility": [
        r"e-?scooter", r"e-?bike", r"micromobility", r"shared.?mobility",
        r"scooter.?rental", r"bike.?share",
    ],
    "Agriculture / Livestock": [
        r"livestock", r"cattle", r"herd", r"farm", r"agri",
        r"irrigation", r"soil.?moisture", r"crop", r"precision.?ag",
    ],
    "Smart Buildings / Facilities": [
        r"smart.?building", r"building.?automation", r"hvac",
        r"facility.?monitor", r"energy.?manage", r"occupancy",
    ],
    "Industrial Monitoring": [
        r"industrial.?sensor", r"thermal.?imag", r"gas.?meter",
        r"telemetry", r"predictive.?maintenance", r"scada",
        r"vibration", r"ultrasound", r"inspection",
    ],
    "Robotics / Autonomous": [
        r"robot", r"drone", r"uav", r"auv", r"autonomous",
        r"unmanned", r"self.?driving", r"teleoperat",
    ],
    "Medical Devices": [
        r"medical.?device", r"patient.?monitor", r"cold.?chain",
        r"remote.?patient", r"telehealth", r"fda",
    ],
    "Supply Chain / Shipping": [
        r"container.?track", r"shipment.?monitor", r"cargo",
        r"cold.?chain", r"logistics.?track", r"reefer",
    ],
    "Connected Vehicles / Equipment": [
        r"connected.?vehicle", r"heavy.?equipment", r"engine.?manufactur",
        r"power.?equipment", r"connect.{0,10}product",
    ],
    "IoT Platform with Hardware": [
        r"iot.?gateway", r"edge.?device", r"iot.?platform",
        r"iot.?hardware", r"iot.?module",
    ],
    "BLE/RFID with Gateway": [
        r"bluetooth.?tag", r"rfid.?track", r"ble.?beacon",
        r"nfc.?device", r"smart.?tag", r"bluetooth.?sensor",
    ],
}


@dataclass
class QualificationResult:
    qualified: str = "N"
    qualification_score: int = 0
    archetype: str = "none"
    hardware_evidence: str | None = None
    connectivity_evidence: str | None = None
    deployment_signals: str | None = None
    matched_categories: list[str] = field(default_factory=list)
    disqualification_reason: str | None = None
    reasoning: str = ""
    confidence_score: float = 0.0
    sources_used: list[str] = field(default_factory=list)


def _count_keyword_hits(text: str, keywords: list[str]) -> list[str]:
    """Return which keywords matched in text."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw in text_lower]


def _match_archetypes(text: str) -> list[str]:
    """Return which archetypes matched based on regex patterns."""
    text_lower = text.lower()
    matched = []
    for archetype, patterns in ARCHETYPE_PATTERNS.items():
        for p in patterns:
            if re.search(p, text_lower):
                matched.append(archetype)
                break
    return matched


def qualify_company(company: dict, waterfall: dict) -> QualificationResult:
    """Qualify a company using the skill's decision criteria as code."""
    result = QualificationResult()
    name = company.get("company_name") or company.get("name", "")
    domain = company.get("company_domain") or company.get("domain", "")
    description = company.get("company_description") or company.get("description") or company.get("leadiq_desc", "")
    notes = company.get("notes", "")
    industry = company.get("industry", "")

    # Combine all text sources
    all_snippets = waterfall.get("all_snippets", "")
    clay_text = f"{description} {notes} {industry}"
    full_text = f"{clay_text} {all_snippets}"

    sources = []

    # ── 1. Domain analysis ─────────────────────────────────
    domain_analysis = waterfall.get("domain_analysis", {})
    if isinstance(domain_analysis, dict) and domain_analysis:
        if domain_analysis.get("is_hard_exclusion"):
            # Check if there's overriding hardware evidence
            hw_hits = _count_keyword_hits(full_text, HARDWARE_KEYWORDS)
            if not hw_hits:
                result.qualified = "N"
                result.qualification_score = 10
                result.confidence_score = 0.85
                result.disqualification_reason = f"Hard exclusion industry: {domain_analysis.get('reasoning', '')}"
                result.reasoning = f"Domain analysis flagged hard exclusion. No hardware evidence found to override."
                result.sources_used = ["domain_analysis"]
                return result
        if domain_analysis.get("keyword_matches"):
            sources.append("domain_analysis")

    # ── 2. Clay data (highest priority) ────────────────────
    clay_hw_hits = _count_keyword_hits(clay_text, HARDWARE_KEYWORDS)
    clay_cell_hits = _count_keyword_hits(clay_text, CELLULAR_KEYWORDS)
    clay_n_hits = _count_keyword_hits(clay_text, STRONG_N_KEYWORDS)

    if clay_hw_hits or clay_cell_hits:
        sources.append("clay_description")

    # ── 3. Search results ──────────────────────────────────
    search_hw_hits = _count_keyword_hits(all_snippets, HARDWARE_KEYWORDS)
    search_cell_hits = _count_keyword_hits(all_snippets, CELLULAR_KEYWORDS)

    if all_snippets:
        # Figure out which search sources contributed
        if waterfall.get("parallel", {}).get("all_snippets"):
            sources.append("parallel")
        if waterfall.get("serper", {}).get("all_snippets"):
            sources.append("serper")
        if waterfall.get("tavily", {}).get("all_snippets"):
            sources.append("tavily")

    homepage = waterfall.get("homepage", {})
    homepage_text = f"{homepage.get('homepage_text', '')} {homepage.get('products_text', '')} {homepage.get('solutions_text', '')}"
    homepage_hw = _count_keyword_hits(homepage_text, HARDWARE_KEYWORDS)
    if homepage_hw:
        sources.append("homepage")

    # ── 4. Combine all evidence ────────────────────────────
    all_hw = list(set(clay_hw_hits + search_hw_hits + homepage_hw))
    all_cell = list(set(clay_cell_hits + search_cell_hits))
    all_archetypes = _match_archetypes(full_text)

    result.matched_categories = all_archetypes
    result.sources_used = sources

    if all_hw:
        result.hardware_evidence = f"Keywords: {', '.join(all_hw[:5])}"
    if all_cell:
        result.connectivity_evidence = f"Keywords: {', '.join(all_cell[:5])}"

    # Pick best archetype
    if all_archetypes:
        result.archetype = all_archetypes[0]

    # ── 5. Scoring ─────────────────────────────────────────
    score = 0

    # Hardware evidence
    if clay_hw_hits:
        score += 35  # Clay description mentions hardware = strong
    if search_hw_hits:
        score += 20  # Search confirms hardware
    if homepage_hw:
        score += 10  # Homepage mentions hardware

    # Cellular/connectivity evidence
    if clay_cell_hits:
        score += 25  # Clay mentions cellular = very strong
    if search_cell_hits:
        score += 15

    # Archetype match
    if all_archetypes:
        score += 10

    # Domain keyword boost
    boost = domain_analysis.get("confidence_boost", 0) if isinstance(domain_analysis, dict) else 0
    score += int(boost * 20)

    # Deployment signals in notes
    deploy_patterns = [r"\d+\s*device", r"\d+\s*unit", r"\d+\s*tracker", r"deploy", r"fleet of"]
    deploy_matches = [p for p in deploy_patterns if re.search(p, full_text.lower())]
    if deploy_matches:
        score += 10
        result.deployment_signals = f"Deployment language found: {', '.join(deploy_matches[:3])}"

    # Cap at 100
    score = min(score, 100)
    result.qualification_score = score

    # ── 6. Verdict ─────────────────────────────────────────
    if score >= 50:
        result.qualified = "Y"
        result.confidence_score = min(0.5 + (score - 50) / 100, 1.0)
        result.disqualification_reason = None
        hw_str = f"Hardware: {', '.join(all_hw[:3])}" if all_hw else "hardware signals in search"
        cell_str = f"Cellular: {', '.join(all_cell[:3])}" if all_cell else ""
        arch_str = f"Archetype: {result.archetype}" if result.archetype != "none" else ""
        result.reasoning = ". ".join(filter(None, [hw_str, cell_str, arch_str]))
    elif score >= 30:
        # Borderline — lean Y per skill rules
        result.qualified = "Y"
        result.confidence_score = 0.3 + (score - 30) / 100
        result.disqualification_reason = None
        result.reasoning = f"Borderline with score {score}. Leaning Y per skill rules (false negative worse than false positive)."
    else:
        result.qualified = "N"
        result.confidence_score = 0.3 + (30 - score) / 100
        if clay_n_hits:
            result.disqualification_reason = f"Strong N signals: {', '.join(clay_n_hits[:3])}"
        elif not all_hw and not all_cell:
            result.disqualification_reason = "No hardware or cellular evidence found in any source"
        else:
            result.disqualification_reason = "Insufficient evidence for qualification"
        result.reasoning = f"Score {score}/100. {result.disqualification_reason}"

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output", type=str, default=str(OUT_PATH))
    args = parser.parse_args()

    with open(CW_PATH) as f:
        companies = json.load(f)

    waterfall_index: dict[str, dict] = {}
    if WATERFALL_PATH.exists():
        with open(WATERFALL_PATH) as f:
            wd = json.load(f)
        for r in wd.get("results", []):
            # Index by name and domain
            cn = r.get("company_name", "")
            cd = r.get("company_domain", "")
            if cn:
                waterfall_index[cn] = r
            if cd:
                waterfall_index[cd] = r

    if args.limit:
        companies = companies[:args.limit]

    total = len(companies)
    print(f"Qualifying {total} closed-won companies (all should be Y)...\n")

    results = []
    y_count = 0
    n_count = 0
    archetype_counts: dict[str, int] = {}
    false_negatives: list[dict] = []

    for i, company in enumerate(companies):
        name = company.get("name", company.get("company_name", ""))
        domain = company.get("domain", company.get("company_domain", ""))

        # Normalize to webhook field names
        normalized = {
            "company_name": name,
            "company_domain": domain,
            "company_description": company.get("description") or company.get("leadiq_desc", ""),
            "notes": company.get("notes", ""),
            "industry": company.get("industry", ""),
        }

        # Find waterfall data
        wf = waterfall_index.get(name) or waterfall_index.get(domain, {})

        result = qualify_company(normalized, wf)

        if result.qualified == "Y":
            y_count += 1
            icon = "Y"
        else:
            n_count += 1
            icon = "N"
            false_negatives.append({"name": name, "domain": domain, "score": result.qualification_score, "reason": result.disqualification_reason})

        arch = result.archetype
        archetype_counts[arch] = archetype_counts.get(arch, 0) + 1

        if args.verbose or result.qualified == "N":
            print(f"  [{i+1}/{total}] [{icon}] {name:40s} score={result.qualification_score:3d}  arch={arch:30s}  conf={result.confidence_score:.2f}")
            if result.qualified == "N":
                print(f"           reason: {result.disqualification_reason}")

        results.append({
            "company_name": name,
            "company_domain": domain,
            **{k: v for k, v in result.__dict__.items()},
        })

    accuracy = y_count / total * 100 if total else 0

    summary = {
        "total": total,
        "qualified_y": y_count,
        "qualified_n": n_count,
        "accuracy_pct": round(accuracy, 1),
        "archetype_distribution": dict(sorted(archetype_counts.items(), key=lambda x: -x[1])),
        "false_negatives": false_negatives,
    }

    with open(Path(args.output), "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print(f"\n{'='*70}")
    print(f"QUALIFICATION RESULTS — {total} Closed-Won Companies")
    print(f"{'='*70}")
    print(f"  Y (correct):  {y_count:3d} ({y_count/total*100:.1f}%)")
    print(f"  N (wrong):    {n_count:3d} ({n_count/total*100:.1f}%)")
    print(f"  ACCURACY:     {accuracy:.1f}%")
    print(f"\nArchetype distribution:")
    for arch, count in sorted(archetype_counts.items(), key=lambda x: -x[1]):
        print(f"  {arch:35s}: {count:3d} ({count/total*100:.0f}%)")

    if false_negatives:
        print(f"\nFalse negatives ({len(false_negatives)}):")
        for fn in false_negatives:
            print(f"  {fn['name']:40s} ({fn['domain']}) score={fn['score']} — {fn['reason']}")

    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
