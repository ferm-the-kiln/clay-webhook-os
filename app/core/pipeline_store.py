import logging
from pathlib import Path

import yaml

from app.models.pipelines import CreatePipelineRequest, PipelineDefinition, PipelineStepConfig, UpdatePipelineRequest

logger = logging.getLogger("clay-webhook-os")


class PipelineStore:
    def __init__(self, pipelines_dir: Path):
        self._dir = pipelines_dir
        self._pipelines: dict[str, PipelineDefinition] = {}

    def load(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        for f in self._dir.glob("*.yaml"):
            try:
                raw = yaml.safe_load(f.read_text())
                if not raw:
                    continue
                steps = []
                for s in raw.get("steps", []):
                    if isinstance(s, str):
                        steps.append(PipelineStepConfig(skill=s))
                    elif isinstance(s, dict):
                        steps.append(PipelineStepConfig(**s))
                pipeline = PipelineDefinition(
                    name=raw.get("name", f.stem),
                    description=raw.get("description", ""),
                    steps=steps,
                    confidence_threshold=raw.get("confidence_threshold", 0.8),
                )
                self._pipelines[pipeline.name] = pipeline
            except Exception as e:
                logger.warning("[pipelines] Failed to load %s: %s", f.name, e)
        logger.info("[pipelines] Loaded %d pipelines", len(self._pipelines))

    def _save(self, name: str) -> None:
        pipeline = self._pipelines.get(name)
        if pipeline is None:
            return
        data = {
            "name": pipeline.name,
            "description": pipeline.description,
            "steps": [s.model_dump(exclude_none=True) for s in pipeline.steps],
            "confidence_threshold": pipeline.confidence_threshold,
        }
        path = self._dir / f"{name}.yaml"
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def list_all(self) -> list[PipelineDefinition]:
        return list(self._pipelines.values())

    def get(self, name: str) -> PipelineDefinition | None:
        return self._pipelines.get(name)

    def create(self, data: CreatePipelineRequest) -> PipelineDefinition:
        pipeline = PipelineDefinition(
            name=data.name,
            description=data.description,
            steps=data.steps,
            confidence_threshold=data.confidence_threshold,
        )
        self._pipelines[pipeline.name] = pipeline
        self._save(pipeline.name)
        return pipeline

    def update(self, name: str, data: UpdatePipelineRequest) -> PipelineDefinition | None:
        pipeline = self._pipelines.get(name)
        if pipeline is None:
            return None
        updates = data.model_dump(exclude_none=True)
        if updates:
            merged = pipeline.model_dump()
            merged.update(updates)
            updated = PipelineDefinition(**merged)
            self._pipelines[name] = updated
            self._save(name)
            return updated
        return pipeline

    def delete(self, name: str) -> bool:
        if name not in self._pipelines:
            return False
        del self._pipelines[name]
        path = self._dir / f"{name}.yaml"
        if path.exists():
            path.unlink()
        return True
