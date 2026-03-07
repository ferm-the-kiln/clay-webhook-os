import json
import logging

from app.config import settings

logger = logging.getLogger("clay-webhook-os")

# Most-generic first → most-specific last (closest to data payload).
_PRIORITY_ORDER = [
    "knowledge_base/frameworks/",
    "knowledge_base/voice/",
    "knowledge_base/objections/",
    "knowledge_base/competitive/",
    "knowledge_base/sequences/",
    "knowledge_base/signals/",
    "knowledge_base/personas/",
    "knowledge_base/industries/",
    "clients/",
]

_CATEGORY_ROLES = {
    "frameworks": "Methodology & frameworks",
    "voice": "Writing style & tone",
    "objections": "Objection handling",
    "competitive": "Competitive intelligence",
    "sequences": "Sequence templates",
    "signals": "Signal patterns",
    "personas": "Persona profiles",
    "industries": "Industry context",
    "clients": "Client profile",
}


def _context_priority(ctx: dict[str, str]) -> int:
    path = ctx["path"]
    for i, prefix in enumerate(_PRIORITY_ORDER):
        if path.startswith(prefix):
            return i
    return len(_PRIORITY_ORDER)


def _get_role(path: str) -> str:
    parts = path.rstrip("/").split("/")
    # clients/foo.md → category "clients"; knowledge_base/voice/x.md → "voice"
    category = parts[0] if parts[0] != "knowledge_base" else parts[1] if len(parts) > 1 else parts[0]
    return _CATEGORY_ROLES.get(category, "Reference")


def build_prompt(
    skill_content: str,
    context_files: list[dict[str, str]],
    data: dict,
    instructions: str | None = None,
) -> str:
    parts: list[str] = []

    # Layer 1: System
    parts.append(
        "You are a JSON generation engine. Return ONLY valid JSON — "
        "no markdown fences, no explanation, no preamble. Just the raw JSON object."
    )

    # Layer 2: Skill
    parts.append(f"\n\n# Skill Instructions\n\n{skill_content}")

    # Layer 3: Context (sorted generic → specific so client context is nearest to data)
    if context_files:
        sorted_ctx = sorted(context_files, key=_context_priority)
        parts.append(f"\n\n---\n\n# Loaded Context ({len(sorted_ctx)} files)\n")
        # Manifest
        for i, ctx in enumerate(sorted_ctx, 1):
            role = _get_role(ctx["path"])
            parts.append(f"{i}. `{ctx['path']}` — {role}")
        parts.append("")
        # Full content
        for ctx in sorted_ctx:
            parts.append(f"\n## {ctx['path']}\n\n{ctx['content']}")

    # Layer 4: Data
    parts.append(f"\n\n---\n\n# Data to Process\n\n{json.dumps(data)}")

    # Layer 5: Instructions
    if instructions:
        parts.append(f"\n\n## Campaign Instructions\n{instructions}")

    # Layer 6: Final reminder
    parts.append("\n\nReturn ONLY the JSON object. No markdown, no explanation.")

    prompt = "".join(parts)

    # Log prompt size
    char_count = len(prompt)
    token_est = char_count // 4
    if token_est > settings.prompt_size_warn_tokens:
        logger.warning(
            "[prompt] Large prompt: chars=%d, tokens_est=%d (threshold=%d)",
            char_count, token_est, settings.prompt_size_warn_tokens,
        )
    else:
        logger.info("[prompt] chars=%d, tokens_est=%d", char_count, token_est)

    return prompt
