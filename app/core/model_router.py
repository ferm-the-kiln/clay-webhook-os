import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger("clay-webhook-os")


@dataclass
class PromptStats:
    token_estimate: int
    context_file_count: int


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def resolve_model(
    *,
    request_model: str | None = None,
    skill_config: dict | None = None,
    prompt: str | None = None,
    context_file_count: int = 0,
) -> str:
    """Resolve which model to use with layered priority.

    Priority order:
    1. Request override (body.model)
    2. Skill frontmatter `model` — explicit model name
    3. Skill frontmatter `model_tier` — mapped via config (light/standard/heavy)
    4. Prompt heuristic (opt-in via enable_smart_routing) — token count + context files
    5. Global default (settings.default_model)
    """
    # Layer 1: explicit request override
    if request_model:
        return request_model

    config = skill_config or {}

    # Layer 2: skill frontmatter explicit model
    if config.get("model"):
        return config["model"]

    # Layer 3: skill frontmatter model_tier
    tier = config.get("model_tier")
    if tier and tier in settings.model_tier_map:
        return settings.model_tier_map[tier]

    # Layer 4: prompt heuristic (opt-in)
    if settings.enable_smart_routing and prompt is not None:
        token_est = _estimate_tokens(prompt)
        thresholds = settings.auto_route_thresholds
        if token_est <= thresholds.get("light_max_tokens", 2000) and context_file_count <= 1:
            logger.info("[model-router] Smart route → haiku (tokens=%d, files=%d)", token_est, context_file_count)
            return settings.model_tier_map.get("light", "haiku")
        if token_est <= thresholds.get("standard_max_tokens", 10000):
            logger.info("[model-router] Smart route → sonnet (tokens=%d, files=%d)", token_est, context_file_count)
            return settings.model_tier_map.get("standard", "sonnet")
        logger.info("[model-router] Smart route → opus (tokens=%d, files=%d)", token_est, context_file_count)
        return settings.model_tier_map.get("heavy", "opus")

    # Layer 5: global default
    return settings.default_model
