import re
from pathlib import Path

from app.config import settings


_skill_cache: dict[str, tuple[float, str]] = {}


def list_skills() -> list[str]:
    if not settings.skills_dir.exists():
        return []
    return sorted(
        d.name
        for d in settings.skills_dir.iterdir()
        if d.is_dir() and (d / "skill.md").exists()
    )


def load_skill(name: str) -> str | None:
    skill_file = settings.skills_dir / name / "skill.md"
    if not skill_file.exists():
        return None

    mtime = skill_file.stat().st_mtime
    cached = _skill_cache.get(name)
    if cached and cached[0] == mtime:
        return cached[1]

    content = skill_file.read_text()
    _skill_cache[name] = (mtime, content)
    return content


def load_skill_variant(name: str, variant_id: str) -> str | None:
    """Load a specific variant of a skill. Returns None if not found."""
    if variant_id == "default":
        return load_skill(name)
    variant_file = settings.skills_dir / name / "variants" / f"{variant_id}.md"
    if not variant_file.exists():
        return None
    return variant_file.read_text()


def parse_context_refs(skill_content: str) -> list[str]:
    pattern = re.compile(
        r"^[-*]\s+(knowledge_base/\S+|clients/\S+|00_foundation/\S+)",
        re.MULTILINE,
    )
    return [m.group(1) for m in pattern.finditer(skill_content)]


def resolve_template_vars(ref_path: str, data: dict) -> str:
    resolved = ref_path
    for var in ("client_slug", "persona_slug"):
        placeholder = "{{" + var + "}}"
        if placeholder in resolved:
            value = data.get(var, "")
            if value:
                resolved = resolved.replace(placeholder, value)
    return resolved


def load_file(relative_path: str) -> str | None:
    full_path = settings.base_dir / relative_path
    if not full_path.exists():
        return None
    return full_path.read_text()


def load_context_files(
    skill_content: str, data: dict
) -> list[dict[str, str]]:
    refs = parse_context_refs(skill_content)
    files = []
    seen = set()

    for ref in refs:
        resolved = resolve_template_vars(ref, data)
        if "{{" in resolved:
            continue
        if resolved in seen:
            continue
        content = load_file(resolved)
        if content:
            seen.add(resolved)
            files.append({"path": resolved, "content": content})

    # Auto-load industry context
    industry = data.get("industry", "")
    if industry:
        slug = re.sub(r"[^a-z0-9]+", "-", industry.lower()).strip("-")
        industries_dir = settings.knowledge_dir / "industries"
        if industries_dir.exists():
            for f in industries_dir.iterdir():
                if not f.suffix == ".md":
                    continue
                stem_prefix = f.stem.split("-")[0]
                if stem_prefix in slug:
                    rel = f"knowledge_base/industries/{f.name}"
                    if rel not in seen:
                        content = f.read_text()
                        seen.add(rel)
                        files.append({"path": rel, "content": content})

    return files
