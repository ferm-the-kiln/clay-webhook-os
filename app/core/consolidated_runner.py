"""Consolidated function execution — merge all AI steps into one claude --print call.

Instead of N separate calls (one per skill step), this module builds a single
mega-prompt with deduplicated context and executes it once. Native API steps
(findymail) still run separately.

Exports build_task_sections() and assemble_prompt() for reuse by the
prepare-consolidated preview endpoint in functions.py.
"""

import json
import logging

from fastapi import Request

from app.config import settings
from app.core.context_assembler import _context_priority, _get_role
from app.core.skill_loader import load_context_files, load_file, load_skill
from app.core.tool_catalog import DEEPLINE_PROVIDERS
from app.models.functions import FunctionDefinition

logger = logging.getLogger("clay-webhook-os")


class ConsolidatedResult:
    """Return value from build_consolidated_prompt."""

    __slots__ = ("prompt", "model", "task_keys", "output_keys", "native_step_indices", "needs_agent")

    def __init__(
        self,
        prompt: str,
        model: str,
        task_keys: list[str],
        output_keys: list[str],
        native_step_indices: list[int],
        needs_agent: bool = False,
    ):
        self.prompt = prompt
        self.model = model
        self.task_keys = task_keys
        self.output_keys = output_keys
        self.native_step_indices = native_step_indices
        self.needs_agent = needs_agent


class TaskSectionsResult:
    """Intermediate result from building task sections."""

    __slots__ = (
        "sections", "context", "seen_paths", "task_keys", "output_hints",
        "native_step_indices", "needs_agent", "task_step_indices", "task_output_keys",
    )

    def __init__(self):
        self.sections: list[str] = []
        self.context: list[dict[str, str]] = []
        self.seen_paths: set[str] = set()
        self.task_keys: list[str] = []
        self.output_hints: list[str] = []  # function-level output hints (for final output format)
        self.native_step_indices: list[int] = []
        self.needs_agent: bool = False
        self.task_step_indices: list[int] = []  # maps each task to its function step index
        self.task_output_keys: list[list[str]] = []  # per-task output key names


# ── Shared helpers (used by both execute and preview paths) ──────────


def build_task_sections(func: FunctionDefinition, data: dict, function_store=None) -> TaskSectionsResult:
    """Build task sections from function steps.

    Handles five step types:
    - skill:* — loads skill.md content + context files
    - call_ai  — uses custom prompt if provided, else falls back to a skill
    - function:* — loads sub-function and inlines its task sections
    - gate — skipped (evaluated at execution time, not in the prompt)
    - provider  — AI fallback prompt with task-aware goal description

    For multi-step functions, intermediate steps use their catalog-level
    output keys (e.g., 'content' for firecrawl) rather than the function's
    final output keys. This allows inter-step data flow via {{variable}}.
    """
    from app.core.tool_catalog import get_step_target_keys

    provider_map = {p["id"]: p for p in DEEPLINE_PROVIDERS}
    ts = TaskSectionsResult()
    total_steps = len(func.steps)

    # Build function-level output hints (used for final step + output format)
    for o in func.outputs:
        hint = f"- {o.key}"
        if o.type:
            hint += f" ({o.type})"
        if o.description:
            hint += f": {o.description}"
        ts.output_hints.append(hint)

    for step_idx, step in enumerate(func.steps):
        tool_id = step.tool
        task_key = f"task_{step_idx + 1}"

        # Resolve {{placeholder}} params with input data
        resolved_params: dict[str, str] = {}
        for key, val in step.params.items():
            resolved = val
            for inp_name, inp_val in data.items():
                resolved = resolved.replace("{{" + str(inp_name) + "}}", str(inp_val))
            resolved_params[key] = resolved

        # Gate steps are evaluated at execution time, not in the prompt
        if tool_id == "gate":
            continue

        # Function steps — load sub-function and inline its task sections
        if tool_id.startswith("function:") and function_store:
            sub_func_id = tool_id.split(":", 1)[1]
            sub_func = function_store.get(sub_func_id)
            if sub_func is None:
                logger.warning("[consolidated] Sub-function '%s' not found, skipping", sub_func_id)
                continue

            # Build sub-function's task sections with merged data
            sub_data = {**data, **resolved_params}
            sub_ts = build_task_sections(sub_func, sub_data, function_store=function_store)

            # Merge sub-function's sections into parent, renaming task keys
            for i, section in enumerate(sub_ts.sections):
                parent_task_key = f"task_{len(ts.task_keys) + 1}"
                sub_task_key = sub_ts.task_keys[i] if i < len(sub_ts.task_keys) else f"task_{i + 1}"
                renamed_section = section.replace(
                    f"===== {sub_task_key.upper()}:",
                    f"===== {parent_task_key.upper()} ({sub_func.name}):",
                    1,
                )
                ts.sections.append(renamed_section)
                ts.task_keys.append(parent_task_key)
                ts.task_step_indices.append(step_idx)
                if i < len(sub_ts.task_output_keys):
                    ts.task_output_keys.append(sub_ts.task_output_keys[i])
                else:
                    ts.task_output_keys.append([o.key for o in sub_func.outputs])

            # Merge context (deduplicated)
            for ctx in sub_ts.context:
                if ctx["path"] not in ts.seen_paths:
                    ts.context.append(ctx)
                    ts.seen_paths.add(ctx["path"])

            # Inherit agent mode
            if sub_ts.needs_agent:
                ts.needs_agent = True

            # Inherit native step indices (offset to parent step index)
            for native_idx in sub_ts.native_step_indices:
                ts.native_step_indices.append(step_idx)

            continue

        # Determine step-appropriate output keys
        step_keys, step_hints = get_step_target_keys(
            tool_id, step_idx, total_steps, func.outputs,
            function_store=function_store,
        )
        is_final = step_idx >= total_steps - 1

        if tool_id.startswith("skill:"):
            skill_name = tool_id.removeprefix("skill:")
            skill_content = load_skill(skill_name)
            if skill_content is None:
                continue

            context_files = load_context_files(
                skill_content, {**data, **resolved_params}, skill_name=skill_name,
            )
            for ctx in context_files:
                if ctx["path"] not in ts.seen_paths:
                    ts.context.append(ctx)
                    ts.seen_paths.add(ctx["path"])

            ts.task_keys.append(task_key)
            ts.task_step_indices.append(step_idx)
            ts.task_output_keys.append(step_keys)
            ts.sections.append(
                f"===== {task_key.upper()}: {skill_name} =====\n\n"
                f"{skill_content}\n\n"
                f"Expected output keys for this task:\n"
                + "\n".join(step_hints)
            )

        elif tool_id == "call_ai":
            custom_prompt = resolved_params.get("prompt")
            # call_ai always targets function outputs (it's the analysis step)
            call_ai_hints = ts.output_hints
            prior_task_keys = [f"task_{i + 1}" for i in range(step_idx)]
            prior_ref = ""
            if prior_task_keys and not is_final:
                prior_ref = ""
            elif prior_task_keys:
                prior_ref = (
                    f"\n\nUse the output from prior tasks ({', '.join(prior_task_keys)}) "
                    f"as context and input data for this analysis."
                )

            if custom_prompt:
                ts.task_keys.append(task_key)
                ts.task_step_indices.append(step_idx)
                ts.task_output_keys.append([o.key for o in func.outputs])
                ts.sections.append(
                    f"===== {task_key.upper()}: AI Analysis =====\n\n"
                    f"{custom_prompt}{prior_ref}\n\n"
                    f"Expected output keys for this task:\n"
                    + "\n".join(call_ai_hints)
                )
            else:
                skill_name = resolved_params.get("skill", "quality-gate")
                skill_content = load_skill(skill_name)
                if skill_content is None:
                    continue

                context_files = load_context_files(
                    skill_content, {**data, **resolved_params}, skill_name=skill_name,
                )
                for ctx in context_files:
                    if ctx["path"] not in ts.seen_paths:
                        ts.context.append(ctx)
                        ts.seen_paths.add(ctx["path"])

                ts.task_keys.append(task_key)
                ts.task_step_indices.append(step_idx)
                ts.task_output_keys.append([o.key for o in func.outputs])
                ts.sections.append(
                    f"===== {task_key.upper()}: AI Analysis ({skill_name}) =====\n\n"
                    f"{skill_content}{prior_ref}\n\n"
                    f"Expected output keys for this task:\n"
                    + "\n".join(call_ai_hints)
                )

        else:
            provider = provider_map.get(tool_id)
            if provider is None:
                continue

            has_native = provider.get("has_native_api", False)
            if has_native and tool_id == "findymail" and settings.findymail_api_key:
                ts.native_step_indices.append(step_idx)
            else:
                if provider.get("execution_mode") == "ai_agent":
                    ts.needs_agent = True

                ts.task_keys.append(task_key)
                ts.task_step_indices.append(step_idx)
                ts.task_output_keys.append(step_keys)
                output_summary = ", ".join(step_keys)

                search_instruction = (
                    "You MUST use WebSearch to find real-time data for this task. "
                    "Do NOT rely on training data alone — search the web and return verified results."
                ) if provider.get("execution_mode") == "ai_agent" else (
                    "Use your knowledge to return accurate, real-world data. "
                    "If you are not confident about a value, return null rather than guessing."
                )

                # For intermediate steps, note that output feeds into later tasks
                flow_note = ""
                if not is_final:
                    flow_note = (
                        f"\n\nNote: This is an intermediate step. Your output ({output_summary}) "
                        f"will be used as input for the next task."
                    )

                ts.sections.append(
                    f"===== {task_key.upper()}: {provider.get('name', tool_id)} =====\n\n"
                    f"You are a precise data lookup agent.\n\n"
                    f"Goal: Given the inputs below, find: {output_summary}.\n\n"
                    f"Inputs:\n"
                    + "\n".join(f"- {k}: {v}" for k, v in resolved_params.items())
                    + f"\n\nExpected output keys:\n"
                    + "\n".join(step_hints)
                    + f"\n\n{search_instruction}"
                    + flow_note
                )

    return ts


def assemble_prompt(
    ts: TaskSectionsResult,
    func: FunctionDefinition,
    data: dict,
    instructions: str | None,
    memory_store=None,
    learning_engine=None,
    context_index=None,
    batch_rows: list[dict] | None = None,
) -> str:
    """Assemble the mega-prompt from task sections, context, and data.

    Supports single-row and batch modes. Shared by execute and preview paths.
    """
    parts: list[str] = []
    n_tasks = len(ts.sections)
    is_batch = batch_rows is not None and len(batch_rows) > 1

    # System instruction — lean for single-task, detailed for multi-task
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

    # Task sections
    parts.append("\n\n# Tasks\n")
    for i, section in enumerate(ts.sections):
        parts.append(f"\n{section}")
        if i < len(ts.sections) - 1:
            parts.append(
                "\nIMPORTANT: Use the output from prior tasks as additional context for this task."
            )

    # Only inject memory, learnings, and semantic context for functions that
    # have content-generation steps (skills or call_ai). Pure data lookup
    # functions (only provider tools) don't need personas, frameworks, etc.
    has_content_steps = bool(ts.context) or any(
        s.tool.startswith("skill:") or s.tool == "call_ai" for s in func.steps
    )

    if has_content_steps:
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
        if ts.context:
            sorted_ctx = sorted(ts.context, key=_context_priority)
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
                if rel_path not in ts.seen_paths:
                    content = load_file(rel_path)
                    if content:
                        parts.append(f"\n## {rel_path}\n\n{content}")

    # Data payload
    if is_batch:
        parts.append(
            "\n\n---\n\n# Rows to Process\n\n"
            "Process each row independently through all tasks above.\n"
        )
        for row_idx, row in enumerate(batch_rows):
            parts.append(f"\n## ROW {row_idx}\n{json.dumps(row)}")
    else:
        parts.append(f"\n\n---\n\n# Data to Process\n\n{json.dumps(data)}")

    # Instructions
    if instructions:
        parts.append(f"\n\n## Campaign Instructions\n{instructions}")

    # Output format
    if is_batch:
        row_schema: dict = {o.key: f"<{o.type}>" for o in func.outputs}
        if n_tasks > 1:
            row_schema = {tk: {o.key: f"<{o.type}>" for o in func.outputs} for tk in ts.task_keys}
        parts.append(
            "\n\n---\n\n# Output Format\n\n"
            "Process each row INDEPENDENTLY through all tasks.\n"
            "Return ONLY a JSON object with this structure:\n"
            f"```\n{json.dumps({'rows': [{'row_id': 'row_0', **row_schema}, {'row_id': 'row_1', '...': '...'}]}, indent=2)}\n```\n\n"
            f"CRITICAL: Return exactly {len(batch_rows)} rows in the 'rows' array, one per input row.\n"
            "Each row is processed independently — do NOT share context between rows.\n"
            "No markdown fences around your actual response — just the raw JSON object."
        )
    elif n_tasks == 1:
        parts.append(
            "\n\n---\n\n# Output Format\n\n"
            "Return ONLY a JSON object with these keys:\n"
            + "\n".join(ts.output_hints)
            + "\n\nNo markdown fences, no explanation — just the raw JSON object."
        )
    else:
        # Build per-task schema using step-specific output keys
        task_schema: dict = {}
        func_output_map = {o.key: (o.type or "string") for o in func.outputs}
        for i, tk in enumerate(ts.task_keys):
            if i < len(ts.task_output_keys):
                keys_for_task = ts.task_output_keys[i]
            else:
                keys_for_task = list(func_output_map.keys())
            task_schema[tk] = {
                k: f"<{func_output_map.get(k, 'string')}>" for k in keys_for_task
            }
        parts.append(
            "\n\n---\n\n# Output Format\n\n"
            "Return ONLY a JSON object with this structure:\n"
            f"```\n{json.dumps(task_schema, indent=2)}\n```\n\n"
            "Each task key contains its own output. "
            "Later tasks should use earlier task outputs as context. "
            "The FINAL task's output keys are the ones that matter most. "
            "No markdown fences around your actual response — just the raw JSON object."
        )

    return "\n".join(parts)


# ── Main entry points ────────────────────────────────────────────────


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
    memory_store = getattr(request.app.state, "memory_store", None)
    context_index = getattr(request.app.state, "context_index", None)
    learning_engine = getattr(request.app.state, "learning_engine", None)
    function_store = getattr(request.app.state, "function_store", None)

    ts = build_task_sections(func, data, function_store=function_store)

    if not ts.sections:
        raise ValueError("No AI steps found in this function")

    prompt = assemble_prompt(
        ts, func, data, instructions,
        memory_store, learning_engine, context_index,
    )

    output_keys = [o.key for o in func.outputs]
    char_count = len(prompt)
    token_est = char_count // 4
    logger.info(
        "[consolidated] Function '%s': %d tasks, %d context files, chars=%d, tokens_est=%d",
        func.id, len(ts.sections), len(ts.context), char_count, token_est,
    )

    return ConsolidatedResult(
        prompt=prompt,
        model=model,
        task_keys=ts.task_keys,
        output_keys=output_keys,
        native_step_indices=ts.native_step_indices,
        needs_agent=ts.needs_agent,
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
