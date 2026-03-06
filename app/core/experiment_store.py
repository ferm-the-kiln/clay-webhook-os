import json
import logging
import shutil
import time
from pathlib import Path

from app.models.experiments import (
    CreateExperimentRequest,
    CreateVariantRequest,
    Experiment,
    ExperimentStatus,
    VariantDef,
    VariantResults,
)

logger = logging.getLogger("clay-webhook-os")


class ExperimentStore:
    def __init__(self, skills_dir: Path, data_dir: Path):
        self._skills_dir = skills_dir
        self._data_dir = data_dir
        self._experiments_file = data_dir / "experiments.json"
        self._experiments: dict[str, Experiment] = {}

    def load(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if self._experiments_file.exists():
            raw = json.loads(self._experiments_file.read_text())
            for item in raw:
                exp = Experiment(**item)
                self._experiments[exp.id] = exp
            logger.info("[experiments] Loaded %d experiments", len(self._experiments))

    def _save_experiments(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        raw = [e.model_dump() for e in self._experiments.values()]
        self._experiments_file.write_text(json.dumps(raw, indent=2))

    # --- Variant CRUD ---

    def list_variants(self, skill: str) -> list[VariantDef]:
        variants_dir = self._skills_dir / skill / "variants"
        if not variants_dir.exists():
            return []
        variants = []
        for f in sorted(variants_dir.glob("*.md")):
            vid = f.stem
            content = f.read_text()
            # Extract label from first line if it starts with #
            lines = content.strip().splitlines()
            label = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else vid
            variants.append(VariantDef(
                id=vid,
                skill=skill,
                label=label,
                content=content,
                created_at=f.stat().st_mtime,
            ))
        return variants

    def get_variant(self, skill: str, variant_id: str) -> VariantDef | None:
        if variant_id == "default":
            skill_file = self._skills_dir / skill / "skill.md"
            if not skill_file.exists():
                return None
            return VariantDef(
                id="default",
                skill=skill,
                label="Default",
                content=skill_file.read_text(),
                created_at=skill_file.stat().st_mtime,
            )
        variant_file = self._skills_dir / skill / "variants" / f"{variant_id}.md"
        if not variant_file.exists():
            return None
        content = variant_file.read_text()
        lines = content.strip().splitlines()
        label = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else variant_id
        return VariantDef(
            id=variant_id,
            skill=skill,
            label=label,
            content=content,
            created_at=variant_file.stat().st_mtime,
        )

    def create_variant(self, skill: str, data: CreateVariantRequest) -> VariantDef:
        variant = VariantDef(skill=skill, label=data.label, content=data.content)
        variants_dir = self._skills_dir / skill / "variants"
        variants_dir.mkdir(parents=True, exist_ok=True)
        variant_file = variants_dir / f"{variant.id}.md"
        variant_file.write_text(data.content)
        return variant

    def update_variant(self, skill: str, variant_id: str, data: CreateVariantRequest) -> VariantDef | None:
        if variant_id == "default":
            return None  # Can't edit default directly
        variant_file = self._skills_dir / skill / "variants" / f"{variant_id}.md"
        if not variant_file.exists():
            return None
        variant_file.write_text(data.content)
        return VariantDef(
            id=variant_id,
            skill=skill,
            label=data.label,
            content=data.content,
        )

    def delete_variant(self, skill: str, variant_id: str) -> bool:
        if variant_id == "default":
            return False
        variant_file = self._skills_dir / skill / "variants" / f"{variant_id}.md"
        if not variant_file.exists():
            return False
        variant_file.unlink()
        return True

    def fork_default(self, skill: str, label: str) -> VariantDef | None:
        """Fork the current default skill.md as a new variant."""
        skill_file = self._skills_dir / skill / "skill.md"
        if not skill_file.exists():
            return None
        content = skill_file.read_text()
        return self.create_variant(skill, CreateVariantRequest(label=label, content=content))

    # --- Experiment CRUD ---

    def list_experiments(self) -> list[Experiment]:
        return list(self._experiments.values())

    def get_experiment(self, exp_id: str) -> Experiment | None:
        return self._experiments.get(exp_id)

    def create_experiment(self, data: CreateExperimentRequest) -> Experiment:
        exp = Experiment(
            skill=data.skill,
            name=data.name,
            variant_ids=data.variant_ids,
        )
        self._experiments[exp.id] = exp
        self._save_experiments()
        return exp

    def delete_experiment(self, exp_id: str) -> bool:
        if exp_id not in self._experiments:
            return False
        del self._experiments[exp_id]
        self._save_experiments()
        return True

    def update_experiment_results(
        self,
        exp_id: str,
        variant_id: str,
        duration_ms: int,
        tokens: int,
    ) -> None:
        exp = self._experiments.get(exp_id)
        if exp is None:
            return
        if variant_id not in exp.results:
            exp.results[variant_id] = VariantResults(variant_id=variant_id)
        r = exp.results[variant_id]
        r.runs += 1
        r.avg_duration_ms = round(
            ((r.avg_duration_ms * (r.runs - 1)) + duration_ms) / r.runs, 1
        )
        r.total_tokens += tokens
        self._save_experiments()

    def complete_experiment(self, exp_id: str) -> None:
        exp = self._experiments.get(exp_id)
        if exp:
            exp.status = ExperimentStatus.completed
            exp.completed_at = time.time()
            self._save_experiments()

    def promote_variant(self, skill: str, variant_id: str) -> bool:
        """Replace skill.md with the variant content, backing up the original."""
        if variant_id == "default":
            return True  # Already the default
        variant = self.get_variant(skill, variant_id)
        if variant is None:
            return False
        skill_file = self._skills_dir / skill / "skill.md"
        if not skill_file.exists():
            return False
        # Backup current default
        backup = self._skills_dir / skill / f"skill.md.backup.{int(time.time())}"
        shutil.copy2(skill_file, backup)
        # Write variant as new default
        skill_file.write_text(variant.content)
        logger.info("[experiments] Promoted variant %s to default for skill %s", variant_id, skill)
        return True
