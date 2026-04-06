"""Named script store — file-based persistence for reusable code blocks.

Scripts are stored as JSON at data/scripts/{name}.json.
Used by script column type and script sources.
"""

import json
import logging
import time
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger("clay-webhook-os")


class ScriptDefinition(BaseModel):
    name: str = Field(..., description="Unique script name (slug)")
    language: str = Field("python", description="python | bash | node")
    code: str = Field("", description="Script source code")
    description: str = Field("", description="Human-readable description")
    inputs: list[str] = Field(default_factory=list, description="Expected input field names")
    outputs: list[str] = Field(default_factory=list, description="Expected output field names")
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class ScriptStore:
    """File-based store for named scripts."""

    def __init__(self, data_dir: str | Path):
        self._dir = Path(data_dir) / "scripts"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._scripts: dict[str, ScriptDefinition] = {}

    def load(self) -> None:
        """Load all scripts from disk."""
        self._scripts.clear()
        for f in self._dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                script = ScriptDefinition(**data)
                self._scripts[script.name] = script
            except Exception as e:
                logger.warning("[script_store] Failed to load %s: %s", f.name, e)
        logger.info("[script_store] Loaded %d scripts", len(self._scripts))

    def get(self, name: str) -> ScriptDefinition | None:
        return self._scripts.get(name)

    def list_all(self) -> list[ScriptDefinition]:
        return sorted(self._scripts.values(), key=lambda s: s.name)

    def create(self, script: ScriptDefinition) -> ScriptDefinition:
        script.created_at = time.time()
        script.updated_at = time.time()
        self._scripts[script.name] = script
        self._save(script)
        logger.info("[script_store] Created script '%s'", script.name)
        return script

    def update(self, name: str, updates: dict) -> ScriptDefinition | None:
        script = self._scripts.get(name)
        if not script:
            return None
        for k, v in updates.items():
            if v is not None and hasattr(script, k):
                setattr(script, k, v)
        script.updated_at = time.time()
        self._save(script)
        return script

    def delete(self, name: str) -> bool:
        if name not in self._scripts:
            return False
        del self._scripts[name]
        path = self._dir / f"{name}.json"
        path.unlink(missing_ok=True)
        logger.info("[script_store] Deleted script '%s'", name)
        return True

    def _save(self, script: ScriptDefinition) -> None:
        path = self._dir / f"{script.name}.json"
        path.write_text(json.dumps(script.model_dump(), indent=2))
