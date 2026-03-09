import json
import logging
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from app.core.context_index import ContextIndex
    from app.core.learning_engine import LearningEngine
    from app.core.memory_store import MemoryStore

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
    memory_store: "MemoryStore | None" = None,
    context_index: "ContextIndex | None" = None,
    skip_semantic: bool = False,
    learning_engine: "LearningEngine | None" = None,
    output_format: str = "json",
) -> str:
    parts: list[str] = []

    # Layer 1: System (format-aware)
    if output_format == "json":
        parts.append(
            "You are a JSON generation engine. Return ONLY valid JSON — "
            "no markdown fences, no explanation, no preamble. Just the raw JSON object."
        )
    elif output_format == "markdown":
        parts.append(
            "You are a content generation engine. Return your output as clean Markdown. "
            "No JSON wrapping, no code fences around the entire output."
        )
    elif output_format == "html":
        parts.append(
            "You are a content generation engine. Return your output as clean HTML. "
            "No JSON wrapping, no markdown, no code fences."
        )
    else:  # text
        parts.append(
            "You are a content generation engine. Return your output as plain text. "
            "No JSON wrapping, no markdown, no code fences."
        )

    # Layer 2: Skill
    parts.append(f"\n\n# Skill Instructions\n\n{skill_content}")

    # Layer 2.5: Memory (prior knowledge about this entity)
    if memory_store is not None:
        entries = memory_store.query(data)
        if entries:
            memory_text = memory_store.format_for_prompt(entries)
            parts.append(f"\n\n---\n\n{memory_text}")
            logger.info("[prompt] Injected %d memory entries", len(entries))

    # Layer 2.7: Learnings from past feedback (persistent corrections)
    if learning_engine is not None:
        client_slug = data.get("client_slug")
        # Extract skill name from the first line of skill_content if possible
        skill_name = None
        for line in skill_content.splitlines():
            if line.startswith("# "):
                skill_name = line[2:].strip().split("—")[0].strip().lower().replace(" ", "-")
                break
        learnings_text = learning_engine.format_for_prompt(
            client_slug=client_slug, skill=skill_name,
        )
        if learnings_text:
            parts.append(f"\n\n---\n\n{learnings_text}")
            logger.info("[prompt] Injected learnings for client=%s skill=%s", client_slug, skill_name)

    # Layer 3: Context (sorted generic → specific so client context is nearest to data)
    seen_paths = {ctx["path"] for ctx in context_files}
    all_context = list(context_files)

    # Layer 3.5: Semantic context (auto-discovered relevant files)
    if context_index is not None and not skip_semantic:
        semantic_hits = context_index.search_by_data(data, top_k=3)
        for rel_path, score in semantic_hits:
            if rel_path in seen_paths:
                continue
            from app.core.skill_loader import load_file
            content = load_file(rel_path)
            if content:
                all_context.append({"path": rel_path, "content": content})
                seen_paths.add(rel_path)
                logger.info("[prompt] Semantic context: %s (score=%.3f)", rel_path, score)

    if all_context:
        sorted_ctx = sorted(all_context, key=_context_priority)
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

    # Layer 6: Final reminder (format-aware)
    if output_format == "json":
        parts.append("\n\nReturn ONLY the JSON object. No markdown, no explanation.")
    elif output_format == "markdown":
        parts.append("\n\nReturn your response as clean Markdown.")
    elif output_format == "html":
        parts.append("\n\nReturn your response as clean HTML.")
    else:
        parts.append("\n\nReturn your response as plain text.")

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


def build_agent_prompts(
    skill_content: str,
    context_files: list[dict[str, str]],
    data: dict,
    instructions: str | None = None,
    memory_store: "MemoryStore | None" = None,
    context_index: "ContextIndex | None" = None,
    skip_semantic: bool = False,
    learning_engine: "LearningEngine | None" = None,
) -> str:
    """Build a prompt for agent-type skills (multi-turn with tool use).

    Unlike build_prompt(), this omits the rigid "return ONLY JSON" wrappers
    since the agent needs freedom to search and reason before producing output.
    The skill.md itself contains the output format instructions.
    """
    parts: list[str] = []

    # Layer 1: Agent role
    parts.append(
        "You are an autonomous research agent. You have access to web search "
        "and web fetch tools. Use them to find real, verifiable information. "
        "After completing your research, return your findings as a single JSON object."
    )

    # Layer 2: Skill instructions
    parts.append(f"\n\n# Skill Instructions\n\n{skill_content}")

    # Layer 2.5: Memory (prior knowledge about this entity)
    if memory_store is not None:
        entries = memory_store.query(data)
        if entries:
            memory_text = memory_store.format_for_prompt(entries)
            parts.append(f"\n\n---\n\n{memory_text}")
            logger.info("[agent-prompt] Injected %d memory entries", len(entries))

    # Layer 2.7: Learnings from past feedback
    if learning_engine is not None:
        client_slug = data.get("client_slug")
        learnings_text = learning_engine.format_for_prompt(client_slug=client_slug)
        if learnings_text:
            parts.append(f"\n\n---\n\n{learnings_text}")

    # Layer 3: Context files (same ordering as build_prompt)
    seen_paths = {ctx["path"] for ctx in context_files}
    all_context = list(context_files)

    # Layer 3.5: Semantic context
    if context_index is not None and not skip_semantic:
        semantic_hits = context_index.search_by_data(data, top_k=3)
        for rel_path, score in semantic_hits:
            if rel_path in seen_paths:
                continue
            from app.core.skill_loader import load_file
            content = load_file(rel_path)
            if content:
                all_context.append({"path": rel_path, "content": content})
                seen_paths.add(rel_path)

    if all_context:
        sorted_ctx = sorted(all_context, key=_context_priority)
        parts.append(f"\n\n---\n\n# Loaded Context ({len(sorted_ctx)} files)\n")
        for i, ctx in enumerate(sorted_ctx, 1):
            role = _get_role(ctx["path"])
            parts.append(f"{i}. `{ctx['path']}` — {role}")
        parts.append("")
        for ctx in sorted_ctx:
            parts.append(f"\n## {ctx['path']}\n\n{ctx['content']}")

    # Layer 4: Data to research
    parts.append(f"\n\n---\n\n# Data to Research\n\n{json.dumps(data)}")

    # Layer 5: Instructions
    if instructions:
        parts.append(f"\n\n## Campaign Instructions\n{instructions}")

    # Layer 6: Final instruction
    parts.append(
        "\n\nResearch the target using your web search tools, then return "
        "your findings as a single JSON object matching the Output Format above. "
        "No markdown fences — just the raw JSON."
    )

    prompt = "".join(parts)

    char_count = len(prompt)
    token_est = char_count // 4
    if token_est > settings.prompt_size_warn_tokens:
        logger.warning(
            "[agent-prompt] Large prompt: chars=%d, tokens_est=%d (threshold=%d)",
            char_count, token_est, settings.prompt_size_warn_tokens,
        )
    else:
        logger.info("[agent-prompt] chars=%d, tokens_est=%d", char_count, token_est)

    return prompt
