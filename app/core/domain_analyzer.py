"""Domain-level signal analysis for company qualification.

Pure functions — no async, no API calls, no state. Analyzes company name
and domain for IoT/cellular keywords to produce a confidence boost and
suggested archetype before any web research runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Keyword → archetype mapping ───────────────────────────────────

IOT_KEYWORDS: dict[str, str] = {
    # GPS / Fleet Tracking
    "gps": "GPS / Fleet Tracking",
    "fleet": "GPS / Fleet Tracking",
    "tracker": "GPS / Fleet Tracking",
    "tracking": "GPS / Fleet Tracking",
    "telematics": "GPS / Fleet Tracking",
    "obd": "GPS / Fleet Tracking",
    "dashcam": "GPS / Fleet Tracking",
    "asset track": "GPS / Fleet Tracking",
    # Micromobility
    "scooter": "Micromobility",
    "e-bike": "Micromobility",
    "ebike": "Micromobility",
    "micromobility": "Micromobility",
    "shared mobility": "Micromobility",
    # Agriculture / Livestock
    "farm": "Agriculture / Livestock",
    "agri": "Agriculture / Livestock",
    "livestock": "Agriculture / Livestock",
    "irrigation": "Agriculture / Livestock",
    "precision agriculture": "Agriculture / Livestock",
    "cattle": "Agriculture / Livestock",
    "herd": "Agriculture / Livestock",
    # Smart Buildings
    "smart building": "Smart Buildings / Facilities",
    "building automation": "Smart Buildings / Facilities",
    "hvac": "Smart Buildings / Facilities",
    "facility monitoring": "Smart Buildings / Facilities",
    # Industrial Monitoring
    "sensor": "Industrial Monitoring",
    "telemetry": "Industrial Monitoring",
    "industrial iot": "Industrial Monitoring",
    "predictive maintenance": "Industrial Monitoring",
    "gas meter": "Industrial Monitoring",
    "thermal imaging": "Industrial Monitoring",
    # Robotics / Autonomous
    "robot": "Robotics / Autonomous",
    "drone": "Robotics / Autonomous",
    "uav": "Robotics / Autonomous",
    "auv": "Robotics / Autonomous",
    "autonomous": "Robotics / Autonomous",
    "unmanned": "Robotics / Autonomous",
    # Medical Devices
    "medical device": "Medical Devices",
    "patient monitoring": "Medical Devices",
    "cold chain": "Medical Devices",
    "medical refriger": "Medical Devices",
    # Supply Chain / Shipping
    "container track": "Supply Chain / Shipping",
    "shipment monitor": "Supply Chain / Shipping",
    "cargo monitor": "Supply Chain / Shipping",
    # Connected Vehicles / Equipment
    "connected vehicle": "Connected Vehicles / Equipment",
    "heavy equipment": "Connected Vehicles / Equipment",
    "engine manufactur": "Connected Vehicles / Equipment",
    # IoT Platform with Hardware
    "iot gateway": "IoT Platform with Hardware",
    "edge device": "IoT Platform with Hardware",
    "iot platform": "IoT Platform with Hardware",
    # Cellular-specific keywords (no archetype — just boost)
    "sim card": "",
    "sim management": "",
    "lte-m": "",
    "cat-m1": "",
    "nb-iot": "",
    "cellular modem": "",
    "cellular connect": "",
    "esim": "",
    "m2m": "",
}

# ── Hard exclusion patterns ───────────────────────────────────────

EXCLUSION_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bbank(ing)?\b",
        r"\bfinancial\s+services?\b",
        r"\binsurance\b",
        r"\bfashion\b",
        r"\bapparel\b",
        r"\bfood\s*&?\s*beverage\b",
        r"\bcpg\b",
        r"\bhr\s+(software|saas|payroll)\b",
        r"\bpayroll\b",
        r"\bmedia\s+(company|publish|group)\b",
        r"\bpublishing\b",
        r"\blegal\s+service\b",
        r"\blaw\s+firm\b",
        r"\bholding\s+compan",
        r"\bprivate\s+equity\b",
        r"\bventure\s+capital\b",
        r"\b(pe|vc)\s+firm\b",
        r"\bdistiller",
        r"\balcohol\b",
        r"\bhospitality\b",
        r"\bhotel\s+(chain|group|management)\b",
        r"\bconsulting\s+(firm|group|compan)\b",
    ]
]


@dataclass
class DomainSignals:
    keyword_matches: dict[str, str] = field(default_factory=dict)  # keyword → archetype
    confidence_boost: float = 0.0  # 0.0–0.3
    suggested_archetype: str = ""
    is_hard_exclusion: bool = False
    reasoning: str = ""


def analyze_domain_signals(
    company_name: str,
    company_domain: str = "",
) -> DomainSignals:
    """Analyze company name + domain for IoT/cellular keyword signals.

    Returns a DomainSignals with keyword matches, confidence boost,
    suggested archetype, and hard-exclusion flag. No API calls.
    """
    text = f"{company_name} {company_domain}".lower()
    signals = DomainSignals()

    # Check hard exclusions first
    for pattern in EXCLUSION_PATTERNS:
        if pattern.search(text):
            signals.is_hard_exclusion = True
            signals.reasoning = f"Hard exclusion: matched '{pattern.pattern}' in name/domain"
            return signals

    # Scan for IoT keywords
    for keyword, archetype in IOT_KEYWORDS.items():
        if keyword in text:
            signals.keyword_matches[keyword] = archetype

    # Calculate confidence boost based on match count
    match_count = len(signals.keyword_matches)
    if match_count >= 3:
        signals.confidence_boost = 0.3
    elif match_count == 2:
        signals.confidence_boost = 0.2
    elif match_count == 1:
        signals.confidence_boost = 0.1

    # Pick the most common archetype from matches
    if signals.keyword_matches:
        archetypes = [a for a in signals.keyword_matches.values() if a]
        if archetypes:
            # Most frequent archetype wins
            signals.suggested_archetype = max(set(archetypes), key=archetypes.count)

    # Build reasoning
    if signals.keyword_matches:
        kw_list = ", ".join(signals.keyword_matches.keys())
        signals.reasoning = (
            f"Found {match_count} IoT keyword(s) in name/domain: {kw_list}. "
            f"Confidence boost: +{signals.confidence_boost}"
        )
        if signals.suggested_archetype:
            signals.reasoning += f". Suggested archetype: {signals.suggested_archetype}"
    else:
        signals.reasoning = "No IoT keywords found in company name or domain"

    return signals
