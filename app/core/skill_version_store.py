import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("clay-webhook-os")


class SkillVersionStore:
    """File-based version history for skill definitions.

    Stores versioned snapshots in data/skill_versions/{skill_name}/v{N}.md
    where N auto-increments starting from 1.
    """

    def __init__(self, data_dir: Path, skills_dir: Path):
        self._dir = data_dir / "skill_versions"
        self._skills_dir = skills_dir

    def load(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        skill_count = sum(1 for d in self._dir.iterdir() if d.is_dir()) if self._dir.exists() else 0
        logger.info("[skill-versions] Loaded version store (%d skills tracked)", skill_count)

    def _skill_dir(self, skill_name: str) -> Path:
        return self._dir / skill_name

    def _version_files(self, skill_name: str) -> list[Path]:
        """Return sorted list of version files for a skill."""
        skill_dir = self._skill_dir(skill_name)
        if not skill_dir.exists():
            return []
        files = sorted(
            (f for f in skill_dir.iterdir() if f.name.startswith("v") and f.name.endswith(".md")),
            key=lambda f: self._parse_version_number(f),
        )
        return files

    @staticmethod
    def _parse_version_number(path: Path) -> int:
        """Extract version number from filename like v3.md -> 3."""
        try:
            return int(path.stem[1:])
        except (ValueError, IndexError):
            return 0

    def get_latest_version(self, skill_name: str) -> int:
        """Return the latest version number, or 0 if no versions exist."""
        files = self._version_files(skill_name)
        if not files:
            return 0
        return self._parse_version_number(files[-1])

    def save_version(self, skill_name: str, content: str) -> int:
        """Save a new version of a skill's content.

        Returns the new version number.
        """
        skill_dir = self._skill_dir(skill_name)
        skill_dir.mkdir(parents=True, exist_ok=True)

        next_version = self.get_latest_version(skill_name) + 1
        version_file = skill_dir / f"v{next_version}.md"
        version_file.write_text(content)

        logger.info("[skill-versions] Saved %s v%d (%d bytes)", skill_name, next_version, len(content))
        return next_version

    def get_versions(self, skill_name: str) -> list[dict]:
        """List all versions for a skill with metadata.

        Returns list of {"version": N, "timestamp": ISO, "size_bytes": int}.
        """
        files = self._version_files(skill_name)
        versions = []
        for f in files:
            stat = f.stat()
            versions.append({
                "version": self._parse_version_number(f),
                "timestamp": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "size_bytes": stat.st_size,
            })
        return versions

    def get_version(self, skill_name: str, version_number: int) -> str | None:
        """Get the full content of a specific version. Returns None if not found."""
        version_file = self._skill_dir(skill_name) / f"v{version_number}.md"
        if not version_file.exists():
            return None
        return version_file.read_text()

    def rollback(self, skill_name: str, version_number: int) -> bool:
        """Copy a specific version back to skills/{skill_name}/skill.md.

        Returns True on success, False if version not found or skill dir missing.
        """
        content = self.get_version(skill_name, version_number)
        if content is None:
            return False

        skill_file = self._skills_dir / skill_name / "skill.md"
        if not skill_file.parent.exists():
            logger.warning("[skill-versions] Skill directory not found: %s", skill_name)
            return False

        skill_file.write_text(content)
        logger.info("[skill-versions] Rolled back %s to v%d", skill_name, version_number)
        return True
