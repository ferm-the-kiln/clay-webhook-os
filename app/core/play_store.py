import logging
import time
from pathlib import Path

import yaml

from app.models.plays import (
    ClayConfigRequest,
    CreatePlayRequest,
    ForkPlayRequest,
    PlayCategory,
    PlayDefinition,
    SchemaField,
    UpdatePlayRequest,
)

logger = logging.getLogger("clay-webhook-os")


class PlayStore:
    def __init__(self, plays_dir: Path, pipelines_dir: Path):
        self._dir = plays_dir
        self._pipelines_dir = pipelines_dir
        self._plays: dict[str, PlayDefinition] = {}

    def load(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        for f in self._dir.glob("*.yaml"):
            try:
                raw = yaml.safe_load(f.read_text())
                if not raw:
                    continue
                raw.setdefault("name", f.stem)
                raw.setdefault("created_at", f.stat().st_mtime)
                # Parse schema fields
                for key in ("input_schema", "output_schema"):
                    if key in raw and isinstance(raw[key], list):
                        raw[key] = [
                            SchemaField(**s) if isinstance(s, dict) else s
                            for s in raw[key]
                        ]
                play = PlayDefinition(**raw)
                self._plays[play.name] = play
            except Exception as e:
                logger.warning("[plays] Failed to load %s: %s", f.name, e)
        logger.info("[plays] Loaded %d plays", len(self._plays))

    def _save(self, name: str) -> None:
        play = self._plays.get(name)
        if play is None:
            return
        data = play.model_dump(exclude_none=True)
        # Convert enums to strings for YAML
        if "category" in data:
            data["category"] = data["category"].value if hasattr(data["category"], "value") else str(data["category"])
        path = self._dir / f"{name}.yaml"
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def list_all(self) -> list[PlayDefinition]:
        return list(self._plays.values())

    def list_by_category(self, category: PlayCategory) -> list[PlayDefinition]:
        return [p for p in self._plays.values() if p.category == category]

    def get(self, name: str) -> PlayDefinition | None:
        return self._plays.get(name)

    def create(self, data: CreatePlayRequest) -> PlayDefinition:
        play = PlayDefinition(
            **data.model_dump(),
            created_at=time.time(),
        )
        self._plays[play.name] = play
        self._save(play.name)
        return play

    def update(self, name: str, data: UpdatePlayRequest) -> PlayDefinition | None:
        play = self._plays.get(name)
        if play is None:
            return None
        updates = data.model_dump(exclude_none=True)
        if updates:
            updated = play.model_copy(update=updates)
            self._plays[name] = updated
            self._save(name)
            return updated
        return play

    def delete(self, name: str) -> bool:
        if name not in self._plays:
            return False
        del self._plays[name]
        path = self._dir / f"{name}.yaml"
        if path.exists():
            path.unlink()
        return True

    def fork(self, name: str, data: ForkPlayRequest) -> PlayDefinition | None:
        original = self._plays.get(name)
        if original is None:
            return None
        fork_data = original.model_dump()
        fork_data["name"] = data.new_name
        fork_data["display_name"] = data.display_name
        fork_data["is_template"] = False
        fork_data["forked_from"] = name
        fork_data["created_at"] = time.time()
        if data.default_model:
            fork_data["default_model"] = data.default_model
        if data.default_confidence_threshold is not None:
            fork_data["default_confidence_threshold"] = data.default_confidence_threshold
        if data.default_instructions is not None:
            fork_data["default_instructions"] = data.default_instructions
        forked = PlayDefinition(**fork_data)
        self._plays[forked.name] = forked
        self._save(forked.name)
        return forked

    def generate_clay_config(self, name: str, req: ClayConfigRequest) -> dict | None:
        play = self._plays.get(name)
        if play is None:
            return None

        # Resolve pipeline → get skill names
        skills = self._resolve_pipeline_skills(play.pipeline)

        # Build data template from input_schema
        data_template: dict = {}
        if req.client_slug:
            data_template["client_slug"] = req.client_slug
        for field in play.input_schema:
            # Convert field name to Clay column placeholder
            col_name = field.name.replace("_", " ").title()
            data_template[field.name] = "{{" + col_name + "}}"

        # Build expected output columns from output_schema
        output_columns = [
            {"name": f.name, "type": f.type, "description": f.description}
            for f in play.output_schema
        ]

        # Build body template
        body_template: dict = {}
        if skills:
            body_template["skills"] = skills
        else:
            body_template["pipeline"] = play.pipeline
        body_template["data"] = data_template
        body_template["model"] = play.default_model
        if play.default_instructions:
            body_template["instructions"] = play.default_instructions

        # Generate setup instructions
        webhook_url = f"{req.api_url}/webhook"
        setup_instructions = [
            "1. In Clay, add an HTTP Action column",
            f"2. Set URL to: {webhook_url}",
            "3. Set Method to: POST",
            "4. Add header: Content-Type = application/json",
            f"5. Add header: X-API-Key = {req.api_key}",
            "6. Paste the body_template JSON into the Body field",
            "7. Map each {{Column Name}} to your Clay table column",
        ]
        if output_columns:
            col_names = ", ".join(c["name"] for c in output_columns)
            setup_instructions.append(f"8. Output columns: {col_names}")

        return {
            "play": name,
            "client_slug": req.client_slug,
            "webhook_url": webhook_url,
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "X-API-Key": req.api_key,
            },
            "body_template": body_template,
            "expected_output_columns": output_columns,
            "setup_instructions": setup_instructions,
        }

    def _resolve_pipeline_skills(self, pipeline_name: str) -> list[str]:
        path = self._pipelines_dir / f"{pipeline_name}.yaml"
        if not path.exists():
            return []
        try:
            raw = yaml.safe_load(path.read_text())
            if not raw:
                return []
            steps = raw.get("steps", [])
            skills = []
            for s in steps:
                if isinstance(s, str):
                    skills.append(s)
                elif isinstance(s, dict):
                    skills.append(s.get("skill", ""))
            return [s for s in skills if s]
        except Exception:
            return []
