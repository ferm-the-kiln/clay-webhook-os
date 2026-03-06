import logging
import re
from pathlib import Path

from app.config import settings
from app.core.context_assembler import build_prompt
from app.core.skill_loader import list_skills, load_context_files, load_skill, parse_context_refs
from app.models.context import (
    ClientProfile,
    ClientSummary,
    CompanyInfo,
    CreateClientRequest,
    KnowledgeBaseFile,
    PromptPreviewResponse,
    TonePreferences,
    UpdateClientRequest,
)

logger = logging.getLogger("clay-webhook-os")


class ContextStore:
    def __init__(
        self,
        clients_dir: Path,
        knowledge_dir: Path,
        skills_dir: Path,
    ):
        self._clients_dir = clients_dir
        self._knowledge_dir = knowledge_dir
        self._skills_dir = skills_dir

    # ── Client CRUD ──────────────────────────────────────────────

    def list_clients(self) -> list[ClientSummary]:
        if not self._clients_dir.exists():
            return []
        results = []
        for f in sorted(self._clients_dir.iterdir()):
            if not f.suffix == ".md" or f.name.startswith("_"):
                continue
            slug = f.stem
            content = f.read_text()
            profile = self._parse_client_markdown(slug, content)
            results.append(
                ClientSummary(
                    slug=profile.slug,
                    name=profile.name,
                    industry=profile.company.industry,
                    stage=profile.company.stage,
                    domain=profile.company.domain,
                )
            )
        return results

    def get_client(self, slug: str) -> ClientProfile | None:
        f = self._clients_dir / f"{slug}.md"
        if not f.exists():
            return None
        content = f.read_text()
        return self._parse_client_markdown(slug, content)

    def create_client(self, data: CreateClientRequest) -> ClientProfile:
        profile = ClientProfile(
            slug=data.slug,
            name=data.name,
            company=data.company,
            what_they_sell=data.what_they_sell,
            icp=data.icp,
            competitive_landscape=data.competitive_landscape,
            recent_news=data.recent_news,
            value_proposition=data.value_proposition,
            tone=data.tone,
            campaign_angles=data.campaign_angles,
            notes=data.notes,
        )
        md = self._render_client_markdown(profile)
        profile.raw_markdown = md
        self._clients_dir.mkdir(parents=True, exist_ok=True)
        (self._clients_dir / f"{data.slug}.md").write_text(md)
        logger.info("[context] Created client: %s", data.slug)
        return profile

    def update_client(self, slug: str, data: UpdateClientRequest) -> ClientProfile | None:
        existing = self.get_client(slug)
        if existing is None:
            return None
        updates = data.model_dump(exclude_none=True)
        updated = existing.model_copy(update=updates)
        md = self._render_client_markdown(updated)
        updated.raw_markdown = md
        (self._clients_dir / f"{slug}.md").write_text(md)
        logger.info("[context] Updated client: %s", slug)
        return updated

    def delete_client(self, slug: str) -> bool:
        f = self._clients_dir / f"{slug}.md"
        if not f.exists():
            return False
        f.unlink()
        logger.info("[context] Deleted client: %s", slug)
        return True

    # ── Knowledge Base ───────────────────────────────────────────

    def list_knowledge_base(self) -> list[KnowledgeBaseFile]:
        if not self._knowledge_dir.exists():
            return []
        results = []
        for f in sorted(self._knowledge_dir.rglob("*.md")):
            rel = f.relative_to(self._knowledge_dir)
            parts = rel.parts
            category = parts[0] if len(parts) > 1 else "general"
            results.append(
                KnowledgeBaseFile(
                    path=str(rel),
                    category=category,
                    name=f.stem,
                    content=f.read_text(),
                )
            )
        return results

    def get_knowledge_file(self, category: str, filename: str) -> KnowledgeBaseFile | None:
        f = self._knowledge_dir / category / filename
        if not f.exists():
            return None
        return KnowledgeBaseFile(
            path=f"{category}/{filename}",
            category=category,
            name=f.stem,
            content=f.read_text(),
        )

    def update_knowledge_file(
        self, category: str, filename: str, content: str
    ) -> KnowledgeBaseFile | None:
        f = self._knowledge_dir / category / filename
        if not f.exists():
            return None
        f.write_text(content)
        logger.info("[context] Updated KB file: %s/%s", category, filename)
        return KnowledgeBaseFile(
            path=f"{category}/{filename}",
            category=category,
            name=f.stem,
            content=content,
        )

    def create_knowledge_file(
        self, category: str, filename: str, content: str
    ) -> KnowledgeBaseFile:
        # Sanitize inputs
        if ".." in category or ".." in filename:
            raise ValueError("Invalid path component")
        for ch in ("/", "\\"):
            if ch in category or ch in filename:
                raise ValueError("Invalid path component")

        # Slugify category
        category = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")

        # Ensure .md extension
        if not filename.endswith(".md"):
            filename = filename + ".md"

        path = self._knowledge_dir / category / filename
        if path.exists():
            raise ValueError("File already exists")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        logger.info("[context] Created KB file: %s/%s", category, filename)
        return KnowledgeBaseFile(
            path=f"{category}/{filename}",
            category=category,
            name=path.stem,
            content=content,
        )

    def delete_knowledge_file(self, category: str, filename: str) -> bool:
        # Sanitize inputs
        if ".." in category or ".." in filename:
            raise ValueError("Invalid path component")
        for ch in ("/", "\\"):
            if ch in category or ch in filename:
                raise ValueError("Invalid path component")

        path = self._knowledge_dir / category / filename
        if not path.exists():
            return False

        path.unlink()
        logger.info("[context] Deleted KB file: %s/%s", category, filename)

        # Remove empty category directory
        cat_dir = self._knowledge_dir / category
        if cat_dir.exists() and not any(cat_dir.iterdir()):
            cat_dir.rmdir()

        return True

    def list_categories(self) -> list[str]:
        if not self._knowledge_dir.exists():
            return []
        return sorted(
            d.name for d in self._knowledge_dir.iterdir() if d.is_dir()
        )

    def get_context_usage_map(self) -> dict[str, list[str]]:
        usage: dict[str, list[str]] = {}
        for skill_name in list_skills():
            content = load_skill(skill_name)
            if content is None:
                continue
            refs = parse_context_refs(content)
            for ref in refs:
                usage.setdefault(ref, []).append(skill_name)
        return usage

    # ── Prompt Preview ───────────────────────────────────────────

    def preview_prompt(
        self, skill: str, client_slug: str, sample_data: dict | None = None
    ) -> PromptPreviewResponse | None:
        skill_content = load_skill(skill)
        if skill_content is None:
            return None
        data = {**(sample_data or {}), "client_slug": client_slug}
        context_files = load_context_files(skill_content, data)
        prompt = build_prompt(skill_content, context_files, data)
        return PromptPreviewResponse(
            assembled_prompt=prompt,
            context_files_loaded=[f["path"] for f in context_files],
            estimated_tokens=len(prompt) // 4,
        )

    # ── Internal: Markdown parsing ───────────────────────────────

    def _parse_client_markdown(self, slug: str, content: str) -> ClientProfile:
        sections = self._split_sections(content)

        # Extract name from H1 or first line
        name = slug.replace("-", " ").title()
        h1_match = re.match(r"^#\s+(.+)", content)
        if h1_match:
            name = h1_match.group(1).strip()

        company = CompanyInfo()
        company_section = sections.get("Company", "")
        if company_section:
            company = CompanyInfo(
                domain=self._extract_bullet(company_section, "Domain"),
                industry=self._extract_bullet(company_section, "Industry"),
                size=self._extract_bullet(company_section, "Size"),
                stage=self._extract_bullet(company_section, "Stage"),
                hq=self._extract_bullet(company_section, "HQ"),
                founded=self._extract_bullet(company_section, "Founded"),
            )

        tone = TonePreferences()
        tone_section = sections.get("Tone Preferences", "")
        if tone_section:
            tone = TonePreferences(
                formality=self._extract_bullet(tone_section, "Formality"),
                approach=self._extract_bullet(tone_section, "Approach"),
                avoid=self._extract_bullet(
                    tone_section, "Things to avoid"
                ) or self._extract_bullet(tone_section, "Avoid"),
            )

        return ClientProfile(
            slug=slug,
            name=name,
            company=company,
            what_they_sell=sections.get("What They Sell", "").strip(),
            icp=sections.get("Target ICP", sections.get("Target ICP — Who Twelve Labs Sells To", "")).strip(),
            competitive_landscape=sections.get("Competitive Landscape", "").strip(),
            recent_news=sections.get(
                "Recent News & Signals (good for personalization)",
                sections.get("Recent News", ""),
            ).strip(),
            value_proposition=sections.get(
                "Value Proposition (for outbound on their behalf)",
                sections.get("Value Proposition", ""),
            ).strip(),
            tone=tone,
            campaign_angles=sections.get(
                "Campaign Angles Worth Testing",
                sections.get("Campaign Angles", sections.get("Campaign Notes", "")),
            ).strip(),
            notes=sections.get("Notes", sections.get("Campaign Notes", "")).strip(),
            raw_markdown=content,
        )

    def _split_sections(self, content: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        current_key: str | None = None
        current_lines: list[str] = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_key is not None:
                    sections[current_key] = "\n".join(current_lines)
                current_key = line[3:].strip()
                current_lines = []
            elif current_key is not None:
                current_lines.append(line)

        if current_key is not None:
            sections[current_key] = "\n".join(current_lines)

        return sections

    def _extract_bullet(self, text: str, key: str) -> str:
        pattern = re.compile(
            rf"[-*]\s+\*\*{re.escape(key)}:\*\*\s*(.+)", re.IGNORECASE
        )
        match = pattern.search(text)
        if match:
            val = match.group(1).strip()
            return val if val != "—" else ""
        return ""

    def _render_client_markdown(self, profile: ClientProfile) -> str:
        lines: list[str] = []
        lines.append(f"# {profile.name}")
        lines.append("")
        lines.append("## Company")
        c = profile.company
        lines.append(f"- **Domain:** {c.domain or '—'}")
        lines.append(f"- **Industry:** {c.industry or '—'}")
        lines.append(f"- **Size:** {c.size or '—'}")
        lines.append(f"- **Stage:** {c.stage or '—'}")
        if c.hq:
            lines.append(f"- **HQ:** {c.hq}")
        if c.founded:
            lines.append(f"- **Founded:** {c.founded}")
        lines.append("")

        if profile.what_they_sell:
            lines.append("## What They Sell")
            lines.append("")
            lines.append(profile.what_they_sell)
            lines.append("")

        if profile.icp:
            lines.append("## Target ICP")
            lines.append("")
            lines.append(profile.icp)
            lines.append("")

        if profile.competitive_landscape:
            lines.append("## Competitive Landscape")
            lines.append("")
            lines.append(profile.competitive_landscape)
            lines.append("")

        if profile.recent_news:
            lines.append("## Recent News")
            lines.append("")
            lines.append(profile.recent_news)
            lines.append("")

        if profile.value_proposition:
            lines.append("## Value Proposition")
            lines.append("")
            lines.append(profile.value_proposition)
            lines.append("")

        lines.append("## Tone Preferences")
        t = profile.tone
        lines.append(f"- **Formality:** {t.formality or '—'}")
        lines.append(f"- **Approach:** {t.approach or '—'}")
        lines.append(f"- **Things to avoid:** {t.avoid or '—'}")
        lines.append("")

        if profile.campaign_angles:
            lines.append("## Campaign Angles")
            lines.append("")
            lines.append(profile.campaign_angles)
            lines.append("")

        if profile.notes:
            lines.append("## Notes")
            lines.append("")
            lines.append(profile.notes)
            lines.append("")

        return "\n".join(lines)
