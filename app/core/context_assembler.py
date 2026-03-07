import json


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

    # Layer 3: Context
    if context_files:
        parts.append("\n\n---\n\n# Loaded Context\n")
        for ctx in context_files:
            parts.append(f"\n## {ctx['path']}\n\n{ctx['content']}")

    # Layer 4: Data
    parts.append(f"\n\n---\n\n# Data to Process\n\n{json.dumps(data)}")

    # Layer 5: Instructions
    if instructions:
        parts.append(f"\n\n## Campaign Instructions\n{instructions}")

    # Layer 6: Final reminder
    parts.append("\n\nReturn ONLY the JSON object. No markdown, no explanation.")

    return "".join(parts)
