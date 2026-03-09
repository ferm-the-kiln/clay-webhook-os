"""Feedback-to-Knowledge Pipeline — closed-loop learning from feedback.

When users submit thumbs-down feedback with notes, the engine:
1. Extracts a persistent learning (stored in knowledge_base/learnings/)
2. Injects top learnings into future prompts for the same client/skill
3. Supports weekly digest generation to surface patterns

Storage: knowledge_base/learnings/{client_slug}.md
Pattern: Append-only markdown with structured sections per skill.
"""

import logging
import re
import time
from pathlib import Path

logger = logging.getLogger("clay-webhook-os")

MAX_LEARNINGS_IN_PROMPT = 10
LEARNINGS_CATEGORY = "learnings"


class LearningEngine:
    def __init__(self, knowledge_dir: Path | str):
        self._learnings_dir = Path(knowledge_dir) / LEARNINGS_CATEGORY
        self._learnings_dir.mkdir(parents=True, exist_ok=True)

    def extract_learning(
        self,
        skill: str,
        client_slug: str | None,
        note: str,
        rating: str = "thumbs_down",
    ) -> dict | None:
        """Extract a learning from feedback and persist it.

        Only processes thumbs_down feedback with non-empty notes.
        Returns the learning dict or None if not applicable.
        """
        if rating != "thumbs_down" or not note or not note.strip():
            return None

        slug = client_slug or "_global"
        timestamp = time.time()
        date_str = time.strftime("%Y-%m-%d", time.localtime(timestamp))

        learning = {
            "skill": skill,
            "client_slug": slug,
            "note": note.strip(),
            "date": date_str,
            "timestamp": timestamp,
        }

        self._append_learning(slug, skill, note.strip(), date_str)
        logger.info(
            "[learning] Extracted learning: skill=%s client=%s note=%.60s",
            skill, slug, note,
        )
        return learning

    def get_learnings(
        self,
        client_slug: str | None = None,
        skill: str | None = None,
        limit: int = MAX_LEARNINGS_IN_PROMPT,
    ) -> list[dict]:
        """Get learnings for a client, optionally filtered by skill."""
        slug = client_slug or "_global"
        path = self._learnings_dir / f"{slug}.md"
        if not path.exists():
            return []

        entries = self._parse_learnings(path)

        if skill:
            entries = [e for e in entries if e["skill"] == skill]

        # Most recent first, capped
        entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        return entries[:limit]

    def format_for_prompt(
        self,
        client_slug: str | None = None,
        skill: str | None = None,
    ) -> str:
        """Format learnings as a prompt section for injection."""
        entries = self.get_learnings(client_slug=client_slug, skill=skill)
        if not entries:
            return ""

        # Also load global learnings if client-specific
        global_entries = []
        if client_slug:
            global_entries = self.get_learnings(client_slug=None, skill=skill, limit=5)

        all_entries = entries + global_entries
        if not all_entries:
            return ""

        lines = [f"# Learnings from Past Feedback ({len(all_entries)} entries)\n"]
        lines.append("IMPORTANT: These are corrections from human reviewers. Follow them strictly.\n")

        for entry in all_entries:
            scope = f"[{entry['skill']}]" if entry.get("skill") else ""
            client_tag = f" ({entry['client_slug']})" if entry.get("client_slug", "_global") != "_global" else ""
            lines.append(f"- {scope}{client_tag} {entry['note']} ({entry.get('date', 'unknown')})")

        return "\n".join(lines)

    def list_clients_with_learnings(self) -> list[str]:
        """List all client slugs that have learnings."""
        return [
            p.stem for p in self._learnings_dir.glob("*.md")
            if p.stem != "_global"
        ]

    def get_digest(self, client_slug: str | None = None) -> dict:
        """Generate a digest of feedback patterns for a client."""
        slug = client_slug or "_global"
        entries = self.get_learnings(client_slug=client_slug, limit=100)

        if not entries:
            return {"client_slug": slug, "total_learnings": 0, "by_skill": {}, "patterns": []}

        # Group by skill
        by_skill: dict[str, list[str]] = {}
        for entry in entries:
            by_skill.setdefault(entry["skill"], []).append(entry["note"])

        # Extract simple patterns (repeated words/phrases)
        all_notes = " ".join(e["note"] for e in entries).lower()
        words = re.findall(r"\b[a-z]{4,}\b", all_notes)
        word_counts: dict[str, int] = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1
        # Filter to words appearing 2+ times, skip common ones
        stop = {"this", "that", "with", "from", "have", "been", "should", "would", "could", "more", "very", "much", "also", "just", "like", "than"}
        patterns = [
            {"term": w, "count": c}
            for w, c in sorted(word_counts.items(), key=lambda x: -x[1])
            if c >= 2 and w not in stop
        ][:10]

        return {
            "client_slug": slug,
            "total_learnings": len(entries),
            "by_skill": {
                sk: {"count": len(notes), "recent": notes[:3]}
                for sk, notes in by_skill.items()
            },
            "patterns": patterns,
        }

    def _append_learning(self, slug: str, skill: str, note: str, date_str: str) -> None:
        """Append a learning entry to the client's learnings file."""
        path = self._learnings_dir / f"{slug}.md"

        if not path.exists():
            header = f"# Learnings — {slug}\n\nFeedback-driven corrections that improve future outputs.\n\n"
            path.write_text(header)

        content = path.read_text()

        # Find or create skill section
        section_header = f"## {skill}"
        if section_header not in content:
            content += f"\n{section_header}\n\n"

        # Append the learning under the skill section
        entry_line = f"- [{date_str}] {note}\n"

        # Insert after the section header
        idx = content.index(section_header) + len(section_header)
        # Find the end of the section header line
        newline_idx = content.index("\n", idx)
        # Skip past the blank line after header if present
        insert_at = newline_idx + 1
        if insert_at < len(content) and content[insert_at] == "\n":
            insert_at += 1

        content = content[:insert_at] + entry_line + content[insert_at:]
        path.write_text(content)

    def _parse_learnings(self, path: Path) -> list[dict]:
        """Parse a learnings markdown file into structured entries."""
        content = path.read_text()
        entries = []
        current_skill = None

        for line in content.splitlines():
            # Detect skill section headers
            if line.startswith("## "):
                current_skill = line[3:].strip()
                continue

            # Parse learning entries: - [YYYY-MM-DD] note text
            match = re.match(r"^- \[(\d{4}-\d{2}-\d{2})\] (.+)$", line)
            if match and current_skill:
                date_str = match.group(1)
                note = match.group(2)
                # Approximate timestamp from date
                try:
                    ts = time.mktime(time.strptime(date_str, "%Y-%m-%d"))
                except ValueError:
                    ts = 0
                entries.append({
                    "skill": current_skill,
                    "client_slug": path.stem,
                    "note": note,
                    "date": date_str,
                    "timestamp": ts,
                })

        return entries
