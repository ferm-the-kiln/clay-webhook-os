"""Cross-client pattern mining from feedback data."""
import logging
import time
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger("clay-webhook-os")


class PatternMiner:
    """Aggregates feedback across clients to discover quality patterns.

    Insights are written to knowledge_base/learnings/_cross_client.md
    and can be used to improve all client outputs.
    """

    def __init__(self, knowledge_dir: Path):
        self._knowledge_dir = knowledge_dir
        self._output_file = knowledge_dir / "learnings" / "_cross_client.md"
        self._last_run: float = 0
        self._last_patterns: list[dict] = []

    def mine(self, feedback_store) -> dict:
        """Analyze all feedback and extract cross-client patterns."""
        self._last_run = time.time()

        # Aggregate feedback by skill
        all_feedback = feedback_store.get_all() if hasattr(feedback_store, "get_all") else []
        if not all_feedback:
            return {"patterns": [], "total_feedback": 0}

        by_skill: dict[str, dict] = defaultdict(lambda: {
            "total": 0,
            "thumbs_up": 0,
            "thumbs_down": 0,
            "clients": set(),
            "down_notes": [],
        })

        for entry in all_feedback:
            skill = getattr(entry, "skill", None) or entry.get("skill", "unknown")
            rating = getattr(entry, "rating", None) or entry.get("rating", "")
            note = getattr(entry, "note", None) or entry.get("note", "")
            client = getattr(entry, "client_slug", None) or entry.get("client_slug", "")

            bucket = by_skill[skill]
            bucket["total"] += 1
            bucket["clients"].add(client)
            if rating == "thumbs_up":
                bucket["thumbs_up"] += 1
            elif rating == "thumbs_down":
                bucket["thumbs_down"] += 1
                if note:
                    bucket["down_notes"].append(note)

        # Build patterns
        patterns = []
        for skill, data in by_skill.items():
            total = data["total"]
            if total < 3:
                continue  # not enough data

            approval_rate = data["thumbs_up"] / total if total > 0 else 0
            patterns.append({
                "skill": skill,
                "total_feedback": total,
                "approval_rate": round(approval_rate, 3),
                "thumbs_up": data["thumbs_up"],
                "thumbs_down": data["thumbs_down"],
                "client_count": len(data["clients"]),
                "common_issues": data["down_notes"][:10],  # top 10 negative notes
            })

        # Sort by lowest approval rate (most problematic first)
        patterns.sort(key=lambda p: p["approval_rate"])

        self._last_patterns = patterns

        # Write cross-client learnings file
        self._write_learnings(patterns)

        return {
            "patterns": patterns,
            "total_feedback": len(all_feedback),
            "skills_analyzed": len(patterns),
            "mined_at": self._last_run,
        }

    def _write_learnings(self, patterns: list[dict]) -> None:
        """Write discovered patterns to knowledge_base/learnings/_cross_client.md."""
        learnings_dir = self._knowledge_dir / "learnings"
        learnings_dir.mkdir(parents=True, exist_ok=True)

        lines = ["# Cross-Client Learnings (Auto-Generated)", ""]
        lines.append(f"Last updated: {time.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        for p in patterns:
            lines.append(f"## {p['skill']}")
            lines.append(f"- Approval rate: {p['approval_rate']*100:.1f}% ({p['thumbs_up']}/{p['total_feedback']})")
            lines.append(f"- Clients: {p['client_count']}")
            if p["common_issues"]:
                lines.append("- Common issues:")
                for issue in p["common_issues"][:5]:
                    lines.append(f"  - {issue}")
            lines.append("")

        self._output_file.write_text("\n".join(lines))
        logger.info("[pattern-miner] Wrote %d patterns to %s", len(patterns), self._output_file)

    def get_latest(self) -> dict:
        """Get the most recent mining results."""
        return {
            "patterns": self._last_patterns,
            "last_run": self._last_run,
        }
