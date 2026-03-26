"""Consolidated function execution — merge all AI steps into one claude --print call.

Instead of N separate calls (one per skill step), this module builds a single
mega-prompt with deduplicated context and executes it once. Native API steps
(findymail) still run separately.
"""

import json
import logging

from fastapi import Request

from app.config import settings
from app.core.context_assembler import _context_priority, _get_role
from app.core.model_router import resolve_model
from app.core.skill_loader import load_context_files, load_file, load_skill, load_skill_config
from app.core.tool_catalog import DEEPLINE_PROVIDERS
from app.models.functions import FunctionDefinition

logger = logging.getLogger("clay-webhook-os")


class ConsolidatedResult:
    """Return value from build_consolidated_prompt."""

    __slots__ = ("prompt", "model", "task_keys", "output_keys", "native_step_indices")

    def __init__(
        self,
        prompt: str,
        model: str,
        task_keys: list[str],
        output_keys: list[str],
        native_step_indices: list[int],
    ):
        self.prompt = prompt
        self.model = model
        self.task_keys = task_keys
        self.output_keys = output_keys
        self.native_step_indices = native_step_indices


def build_consolidated_prompt(
    func: FunctionDefinition,
    data: dict,
    instructions: str | None,
    model: str,
    request: Request,
) -> ConsolidatedResult:
    """Build a single mega-prompt combining all AI steps in a function.

    Returns a ConsolidatedResult with the prompt, resolved model, task keys,
    output keys, and indices of steps that need native API execution.
    """
    provider_map = {p["id"]: p for p in DEEPLINE_PROVIDERS}
    memory_store = getattr(request.app.state, "memory_store", None)
    context_index = getattr(request.app.state, "context_index", None)
    learning_engine = getattr(request.app.state, "learning_engine", None)

    task_sections: list[str] = []
    all_context: list[dict[str, str]] = []
    seen_context_paths: set[str] = set()
    task_keys: list[str] = []
    native_step_indices: list[int] = []
    output_keys = [o.key for o in func.outputs]

    # Build output hints once
    output_hints: list[str] = []
    for o in func.outputs:
        hint = f"- {o.key}"
        if o.type:
            hint += f" ({o.type})"
        if o.description:
            hint += f": {o.description}"
        output_hints.append(hint)

    for step_idx, step in enumerate(func.steps):
        tool_id = step.tool
        task_key = f"task_{step_idx + 1}"

        # Resolve params
        resolved_params: dict[str, str] = {}
        for key, val in step.params.items():
            resolved = val
            for inp_name, inp_val in data.items():
                resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
            resolved_params[key] = resolved

        if tool_id.startswith("skill:"):
            skill_name = tool_id.removeprefix("skill:")
            skill_content = load_skill(skill_name)
            if skill_content is None:
                continue

            skill_config = load_skill_config(skill_name)
            resolve_model(request_model=model, skill_config=skill_config)

            context_files = load_context_files(
                skill_content, {**data, **resolved_params}, skill_name=skill_name,
            )
            for ctx in context_files:
                if ctx["path"] not in seen_context_paths:
                    all_context.append(ctx)
                    seen_context_paths.add(ctx["path"])

            task_keys.append(task_key)
            task_sections.append(
                f"===== {task_key.upper()}: {skill_name} =====\n\n"
                f"{skill_content}\n\n"
                f"Expected output keys for this task:\n"
                + "\n".join(output_hints)
            )

        elif tool_id == "call_ai":
            skill_name = resolved_params.get("skill", "quality-gate")
            skill_content = load_skill(skill_name)
            if skill_content is None:
                continue

            context_files = load_context_files(
                skill_content, {**data, **resolved_params}, skill_name=skill_name,
            )
            for ctx in context_files:
                if ctx["path"] not in seen_context_paths:
                    all_context.append(ctx)
                    seen_context_paths.add(ctx["path"])

            task_keys.append(task_key)
            task_sections.append(
                f"===== {task_key.upper()}: AI Analysis ({skill_name}) =====\n\n"
                f"{skill_content}\n\n"
                f"Expected output keys for this task:\n"
                + "\n".join(output_hints)
            )

        else:
            provider = provider_map.get(tool_id)
            if provider is None:
                continue

            has_native = provider.get("has_native_api", False)
            if has_native and tool_id == "findymail" and settings.findymail_api_key:
                native_step_indices.append(step_idx)
            else:
                task_keys.append(task_key)
                # Build a task-aware prompt using the output keys to describe the goal
                output_summary = ", ".join(o.key for o in func.outputs if o.description)
                task_sections.append(
                    f"===== {task_key.upper()}: {provider.get('name', tool_id)} =====\n\n"
                    f"You are a precise data lookup agent.\n\n"
                    f"Goal: Given the inputs below, find: {output_summary}.\n\n"
                    f"Inputs:\n"
                    + "\n".join(f"- {k}: {v}" for k, v in resolved_params.items())
                    + f"\n\nExpected output keys:\n"
                    + "\n".join(output_hints)
                    + "\n\nUse your knowledge to return accurate, real-world data. "
                    "If you are not confident about a value, return null rather than guessing."
                )

    if not task_sections:
        raise ValueError("No AI steps found in this function")

    # --- Build the mega-prompt ---
    parts: list[str] = []

    n_tasks = len(task_sections)
    if n_tasks == 1:
        parts.append(
            "You are a precise JSON generation engine.\n\n"
            "Execute the task below and return ONLY a single JSON object — "
            "no markdown fences, no explanation."
        )
    else:
        parts.append(
            f"You are a multi-step JSON generation engine.\n\n"
            f"You will execute {n_tasks} tasks sequentially. "
            f"Each task's output is available as context for subsequent tasks.\n\n"
            f"Return ONLY a single JSON object — no markdown fences, no explanation."
        )

    parts.append("\n\n# Tasks\n")
    for i, section in enumerate(task_sections):
        parts.append(f"\n{section}")
        if i < len(task_sections) - 1:
            parts.append(
                "\nIMPORTANT: Use the output from prior tasks as additional context for this task."
            )

    # Memory
    if memory_store is not None:
        entries = memory_store.query(data)
        if entries:
            memory_text = memory_store.format_for_prompt(entries)
            parts.append(f"\n\n---\n\n{memory_text}")

    # Learnings
    if learning_engine is not None:
        client_slug = data.get("client_slug")
        learnings_text = learning_engine.format_for_prompt(client_slug=client_slug)
        if learnings_text:
            parts.append(f"\n\n---\n\n{learnings_text}")

    # Context files (deduplicated, sorted generic → specific)
    if all_context:
        sorted_ctx = sorted(all_context, key=_context_priority)
        parts.append(f"\n\n---\n\n# Loaded Context ({len(sorted_ctx)} files, deduplicated)\n")
        for i, ctx in enumerate(sorted_ctx, 1):
            role = _get_role(ctx["path"])
            parts.append(f"{i}. `{ctx['path']}` — {role}")
        parts.append("")
        for ctx in sorted_ctx:
            parts.append(f"\n## {ctx['path']}\n\n{ctx['content']}")

    # Semantic context
    if context_index is not None:
        semantic_hits = context_index.search_by_data(data, top_k=3)
        for rel_path, score in semantic_hits:
            if rel_path not in seen_context_paths:
                content = load_file(rel_path)
                if content:
                    parts.append(f"\n## {rel_path}\n\n{content}")

    # Data payload
    parts.append(f"\n\n---\n\n# Data to Process\n\n{json.dumps(data)}")

    # Instructions
    if instructions:
        parts.append(f"\n\n## Campaign Instructions\n{instructions}")

    # Output format
    if n_tasks == 1:
        parts.append(
            "\n\n---\n\n# Output Format\n\n"
            "Return ONLY a JSON object with these keys:\n"
            + "\n".join(output_hints)
            + "\n\nNo markdown fences, no explanation — just the raw JSON object."
        )
    else:
        task_schema = {tk: {o.key: f"<{o.type}>" for o in func.outputs} for tk in task_keys}
        parts.append(
            "\n\n---\n\n# Output Format\n\n"
            "Return ONLY a JSON object with this structure:\n"
            f"```\n{json.dumps(task_schema, indent=2)}\n```\n\n"
            "Each task key contains its own output. "
            "Later tasks can refine/override earlier task outputs. "
            "No markdown fences around your actual response — just the raw JSON object."
        )

    prompt = "\n".join(parts)

    char_count = len(prompt)
    token_est = char_count // 4
    logger.info(
        "[consolidated] Function '%s': %d tasks, %d context files, chars=%d, tokens_est=%d",
        func.id, n_tasks, len(all_context), char_count, token_est,
    )

    return ConsolidatedResult(
        prompt=prompt,
        model=model,
        task_keys=task_keys,
        output_keys=output_keys,
        native_step_indices=native_step_indices,
    )


def parse_consolidated_output(
    raw: dict,
    task_keys: list[str],
    output_keys: list[str],
) -> dict:
    """Extract final output from a consolidated response.

    Single-task: returns raw output directly.
    Multi-task: merges all task outputs (later tasks override earlier).
    """
    if len(task_keys) <= 1:
        return raw

    merged: dict = {}
    for tk in task_keys:
        task_output = raw.get(tk)
        if isinstance(task_output, dict):
            merged.update(task_output)

    # Fallback: if model returned flat keys instead of task_1/task_2
    if not merged:
        for key in output_keys:
            if key in raw:
                merged[key] = raw[key]

    return merged
