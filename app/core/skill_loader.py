import re

import yaml

from app.config import settings


_skill_cache: dict[str, tuple[float, dict, str]] = {}


def list_skills() -> list[str]:
    if not settings.skills_dir.exists():
        return []
    return sorted(
        d.name
        for d in settings.skills_dir.iterdir()
        if d.is_dir() and (d / "skill.md").exists()
    )


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from skill content.

    Returns (frontmatter_dict, body_without_frontmatter).
    If no frontmatter, returns ({}, original_content).
    """
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 3:].lstrip("\n")
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}, content
    return fm, body


def load_skill(name: str) -> str | None:
    skill_file = settings.skills_dir / name / "skill.md"
    if not skill_file.exists():
        return None

    mtime = skill_file.stat().st_mtime
    cached = _skill_cache.get(name)
    if cached and cached[0] == mtime:
        return cached[2]

    content = skill_file.read_text()
    fm, body = parse_frontmatter(content)
    _skill_cache[name] = (mtime, fm, body)
    return body


def load_skill_config(name: str) -> dict:
    """Return the frontmatter config dict for a skill."""
    skill_file = settings.skills_dir / name / "skill.md"
    if not skill_file.exists():
        return {}

    mtime = skill_file.stat().st_mtime
    cached = _skill_cache.get(name)
    if cached and cached[0] == mtime:
        return cached[1]

    content = skill_file.read_text()
    fm, body = parse_frontmatter(content)
    _skill_cache[name] = (mtime, fm, body)
    return fm


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
    # Support structured client directories: clients/{slug}.md -> clients/{slug}/profile.md
    if resolved.startswith("clients/") and resolved.endswith(".md") and not resolved.endswith("/profile.md"):
        profile_path = resolved[:-3] + "/profile.md"
        full_profile = settings.base_dir / profile_path
        if full_profile.exists():
            return profile_path
    return resolved


def load_file(relative_path: str) -> str | None:
    full_path = settings.base_dir / relative_path
    if not full_path.exists():
        return None
    return full_path.read_text()


def load_context_files(
    skill_content: str, data: dict, *, skill_name: str | None = None
) -> list[dict[str, str]]:
    files = []
    seen = set()

    # --- Defaults layer: auto-load knowledge_base/_defaults/*.md ---
    # Skills can opt out with `skip_defaults: true` in frontmatter
    skip_defaults = False
    if skill_name:
        config = load_skill_config(skill_name)
        skip_defaults = config.get("skip_defaults", False)

    defaults_dir = settings.knowledge_dir / "_defaults"
    if not skip_defaults and defaults_dir.exists():
        for f in sorted(defaults_dir.iterdir()):
            if f.suffix == ".md":
                rel = f"knowledge_base/_defaults/{f.name}"
                content = f.read_text()
                seen.add(rel)
                files.append({"path": rel, "content": content})

    # --- Context refs: from frontmatter (preferred) or regex fallback ---
    context_max_chars = None
    if skill_name:
        # config already loaded above for skip_defaults check
        refs = config.get("context", []) or []
        context_max_chars = config.get("context_max_chars")
        if not refs:
            refs = parse_context_refs(skill_content)
    else:
        refs = parse_context_refs(skill_content)

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

    # --- Auto-load industry context (exact slug match) ---
    industry = data.get("industry", "")
    if industry:
        slug = re.sub(r"[^a-z0-9]+", "-", industry.lower()).strip("-")
        industries_dir = settings.knowledge_dir / "industries"
        if industries_dir.exists():
            industry_file = industries_dir / f"{slug}.md"
            if industry_file.exists():
                rel = f"knowledge_base/industries/{slug}.md"
                if rel not in seen:
                    content = industry_file.read_text()
                    seen.add(rel)
                    files.append({"path": rel, "content": content})

    # --- Truncate context files if context_max_chars is set ---
    if context_max_chars and isinstance(context_max_chars, int):
        for ctx in files:
            if len(ctx["content"]) > context_max_chars:
                ctx["content"] = ctx["content"][:context_max_chars] + "\n\n[...truncated]"

    return files


# ── CRUD helpers ─────────────────────────────────────────────

def get_skill_raw(name: str) -> str | None:
    """Read skill.md content including frontmatter (no stripping)."""
    skill_file = settings.skills_dir / name / "skill.md"
    if not skill_file.exists():
        return None
    return skill_file.read_text()


def save_skill(name: str, content: str) -> bool:
    """Write content to an existing skill.md and invalidate cache."""
    skill_file = settings.skills_dir / name / "skill.md"
    if not skill_file.exists():
        return False
    skill_file.write_text(content)
    _skill_cache.pop(name, None)
    return True


def create_skill(name: str, content: str) -> bool:
    """Create a new skill directory with skill.md. Returns False if exists."""
    skill_dir = settings.skills_dir / name
    if skill_dir.exists():
        return False
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.md").write_text(content)
    return True


def delete_skill(name: str) -> bool:
    """Remove a skill directory entirely and invalidate cache."""
    import shutil

    skill_dir = settings.skills_dir / name
    if not skill_dir.exists():
        return False
    shutil.rmtree(skill_dir)
    _skill_cache.pop(name, None)
    return True
