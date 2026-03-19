"""Parse skill chain DSL strings into executable step lists.

Syntax:
    email-gen → quality-gate
    email-gen → quality-gate | if confidence_score < 0.7 → email-gen(retry=true)
    classify → email-gen(model=sonnet) → quality-gate

Operators:
    →  : pipe output to next skill
    |  : conditional gate (if field op value)
    () : override params for that step
"""
import logging
import re

logger = logging.getLogger("clay-webhook-os")


def parse_chain(chain_str: str) -> list[dict]:
    """Parse a chain DSL string into a list of step dicts.

    Returns:
        [{"skill": "email-gen", "condition": None, "params": {}}, ...]
    """
    if not chain_str or not chain_str.strip():
        return []

    steps = []
    # Split on → (arrow) — handle both → and ->
    raw_steps = re.split(r"\s*(?:→|->)\s*", chain_str.strip())

    for raw_step in raw_steps:
        raw_step = raw_step.strip()
        if not raw_step:
            continue

        step = _parse_step(raw_step)
        if step:
            steps.append(step)

    return steps


def _parse_step(raw: str) -> dict | None:
    """Parse a single step which may have a condition prefix and params suffix.

    Examples:
        "email-gen"
        "email-gen(model=sonnet)"
        "if confidence_score < 0.7"  (condition-only, attaches to next step concept)
        "quality-gate | if confidence_score < 0.7"
    """
    condition = None
    params = {}

    # Check for condition: "skill | if field op value" or "if field op value"
    if "| if " in raw:
        parts = raw.split("| if ", 1)
        skill_part = parts[0].strip()
        condition = _parse_condition(parts[1].strip())
    elif raw.startswith("if "):
        # Standalone condition — return it so the caller can handle
        condition = _parse_condition(raw[3:].strip())
        return {"skill": None, "condition": condition, "params": {}}
    else:
        skill_part = raw

    # Extract params: skill_name(key=val, key2=val2)
    param_match = re.match(r"^([\w-]+)\((.+)\)$", skill_part)
    if param_match:
        skill_name = param_match.group(1)
        params = _parse_params(param_match.group(2))
    else:
        skill_name = skill_part.strip()

    if not skill_name:
        return None

    return {"skill": skill_name, "condition": condition, "params": params}


def _parse_condition(cond_str: str) -> dict | None:
    """Parse 'field op value' into a condition dict.

    Examples:
        "confidence_score < 0.7" → {"field": "confidence_score", "op": "<", "value": 0.7}
        "status == approved" → {"field": "status", "op": "==", "value": "approved"}
    """
    match = re.match(r"^(\w+)\s*(>=|<=|!=|==|>|<)\s*(.+)$", cond_str.strip())
    if not match:
        logger.warning("[chain-parser] Could not parse condition: %s", cond_str)
        return None

    field = match.group(1)
    op = match.group(2)
    raw_value = match.group(3).strip()

    # Try numeric conversion
    try:
        value = float(raw_value)
        if value == int(value):
            value = int(value)
    except ValueError:
        value = raw_value.strip("\"'")

    return {"field": field, "op": op, "value": value}


def _parse_params(params_str: str) -> dict:
    """Parse 'key=val, key2=val2' into a dict."""
    params = {}
    for pair in params_str.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        key, val = pair.split("=", 1)
        params[key.strip()] = val.strip().strip("\"'")
    return params


def evaluate_condition(condition: dict, data: dict) -> bool:
    """Evaluate a condition against output data."""
    if condition is None:
        return True

    field = condition["field"]
    op = condition["op"]
    expected = condition["value"]
    actual = data.get(field)

    if actual is None:
        return False

    # Coerce to same type for comparison
    try:
        if isinstance(expected, (int, float)):
            actual = float(actual)
    except (ValueError, TypeError):
        return False

    ops = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "<": lambda a, b: a < b,
        ">": lambda a, b: a > b,
        "<=": lambda a, b: a <= b,
        ">=": lambda a, b: a >= b,
    }

    return ops.get(op, lambda a, b: False)(actual, expected)


def chain_to_skill_list(chain_str: str) -> list[str]:
    """Extract just the skill names from a chain DSL (for validation)."""
    steps = parse_chain(chain_str)
    return [s["skill"] for s in steps if s.get("skill")]
