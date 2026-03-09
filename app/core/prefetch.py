import logging

logger = logging.getLogger("clay-webhook-os")


def parse_research_config(config: dict) -> set[str]:
    """Parse 'research' field from skill frontmatter. Returns set of research intents.

    Falls back to legacy 'prefetch' field for backward compatibility:
      - prefetch: sumble → company_profile
      - prefetch: exa → ignored (retired)
    """
    # New format: research: [company_profile, company_intel]
    val = config.get("research")
    if val is not None:
        if isinstance(val, str):
            return {val}
        if isinstance(val, list):
            return set(val)
        return set()

    # Legacy format: prefetch: sumble / prefetch: [exa, sumble]
    val = config.get("prefetch")
    if val is None:
        return set()
    names = [val] if isinstance(val, str) else val if isinstance(val, list) else []
    result = set()
    for n in names:
        if n == "sumble":
            result.add("company_profile")
        # exa → retired, ignored
    return result


# Backward compat alias
parse_prefetch_config = parse_research_config
