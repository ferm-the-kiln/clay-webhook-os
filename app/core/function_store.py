import logging
import re
import time
from pathlib import Path

import yaml

from app.models.functions import (
    CreateFolderRequest,
    CreateFunctionRequest,
    FolderDefinition,
    FunctionClayConfig,
    FunctionDefinition,
    FunctionInput,
    FunctionOutput,
    FunctionStep,
    MoveFunctionRequest,
    RenameFolderRequest,
    UpdateFunctionRequest,
)

logger = logging.getLogger("clay-webhook-os")


def _slugify(name: str) -> str:
    """Convert a display name to a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "untitled"


class FunctionStore:
    def __init__(self, functions_dir: Path):
        self._dir = functions_dir
        self._functions: dict[str, FunctionDefinition] = {}
        self._folders: dict[str, FolderDefinition] = {}

    def load(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

        # Load folders metadata
        folders_file = self._dir / "_folders.yaml"
        if folders_file.exists():
            try:
                raw = yaml.safe_load(folders_file.read_text()) or []
                for f in raw:
                    folder = FolderDefinition(**f)
                    self._folders[folder.name] = folder
            except Exception as e:
                logger.warning("[functions] Failed to load folders: %s", e)

        # Load function YAML files
        for f in self._dir.glob("*.yaml"):
            if f.name.startswith("_"):
                continue
            try:
                raw = yaml.safe_load(f.read_text())
                if not raw:
                    continue
                func = self._parse_function(f.stem, raw)
                self._functions[func.id] = func
                # Auto-create folder if referenced but not defined
                if func.folder and func.folder not in self._folders:
                    self._folders[func.folder] = FolderDefinition(name=func.folder)
            except Exception as e:
                logger.warning("[functions] Failed to load %s: %s", f.name, e)

        # Ensure "Uncategorized" folder exists
        if "Uncategorized" not in self._folders:
            self._folders["Uncategorized"] = FolderDefinition(name="Uncategorized", order=999)

        logger.info("[functions] Loaded %d functions in %d folders", len(self._functions), len(self._folders))

    def _parse_function(self, file_id: str, raw: dict) -> FunctionDefinition:
        inputs = [FunctionInput(**i) for i in raw.get("inputs", [])]
        outputs = [FunctionOutput(**o) for o in raw.get("outputs", [])]
        steps = [FunctionStep(**s) for s in raw.get("steps", [])]
        clay_config = None
        if raw.get("clay_config"):
            clay_config = FunctionClayConfig(**raw["clay_config"])

        return FunctionDefinition(
            id=raw.get("id", file_id),
            name=raw.get("name", file_id),
            description=raw.get("description", ""),
            folder=raw.get("folder", "Uncategorized"),
            inputs=inputs,
            outputs=outputs,
            steps=steps,
            clay_config=clay_config,
            created_at=raw.get("created_at", 0),
            updated_at=raw.get("updated_at", 0),
        )

    def _save_function(self, func: FunctionDefinition) -> None:
        data = {
            "id": func.id,
            "name": func.name,
            "description": func.description,
            "folder": func.folder,
            "inputs": [i.model_dump() for i in func.inputs],
            "outputs": [o.model_dump() for o in func.outputs],
            "steps": [s.model_dump() for s in func.steps],
            "created_at": func.created_at,
            "updated_at": func.updated_at,
        }
        if func.clay_config:
            data["clay_config"] = func.clay_config.model_dump()
        path = self._dir / f"{func.id}.yaml"
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def _save_folders(self) -> None:
        folders_file = self._dir / "_folders.yaml"
        data = [f.model_dump() for f in sorted(self._folders.values(), key=lambda f: f.order)]
        folders_file.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    # ── Function CRUD ─────────────────────────────────────

    def list_all(self) -> list[FunctionDefinition]:
        return list(self._functions.values())

    def list_by_folder(self, folder: str) -> list[FunctionDefinition]:
        return [f for f in self._functions.values() if f.folder == folder]

    def search(self, query: str) -> list[FunctionDefinition]:
        q = query.lower()
        return [
            f for f in self._functions.values()
            if q in f.name.lower() or q in f.description.lower()
        ]

    def get(self, func_id: str) -> FunctionDefinition | None:
        return self._functions.get(func_id)

    def create(self, data: CreateFunctionRequest) -> FunctionDefinition:
        func_id = _slugify(data.name)
        # Handle duplicate IDs
        base_id = func_id
        counter = 1
        while func_id in self._functions:
            func_id = f"{base_id}-{counter}"
            counter += 1

        now = time.time()
        func = FunctionDefinition(
            id=func_id,
            name=data.name,
            description=data.description,
            folder=data.folder,
            inputs=data.inputs,
            outputs=data.outputs,
            steps=data.steps,
            clay_config=data.clay_config,
            created_at=now,
            updated_at=now,
        )
        self._functions[func.id] = func
        self._save_function(func)

        # Auto-create folder if new
        if func.folder and func.folder not in self._folders:
            self._folders[func.folder] = FolderDefinition(name=func.folder)
            self._save_folders()

        return func

    def update(self, func_id: str, data: UpdateFunctionRequest) -> FunctionDefinition | None:
        func = self._functions.get(func_id)
        if func is None:
            return None

        updates = data.model_dump(exclude_none=True)
        if not updates:
            return func

        current = func.model_dump()
        current.update(updates)
        current["updated_at"] = time.time()
        updated = FunctionDefinition(**current)
        self._functions[func_id] = updated
        self._save_function(updated)

        # Auto-create folder if new
        if updated.folder and updated.folder not in self._folders:
            self._folders[updated.folder] = FolderDefinition(name=updated.folder)
            self._save_folders()

        return updated

    def delete(self, func_id: str) -> bool:
        if func_id not in self._functions:
            return False
        del self._functions[func_id]
        path = self._dir / f"{func_id}.yaml"
        if path.exists():
            path.unlink()
        return True

    def move(self, func_id: str, data: MoveFunctionRequest) -> FunctionDefinition | None:
        func = self._functions.get(func_id)
        if func is None:
            return None
        func.folder = data.folder
        func.updated_at = time.time()
        self._functions[func_id] = func
        self._save_function(func)

        if data.folder not in self._folders:
            self._folders[data.folder] = FolderDefinition(name=data.folder)
            self._save_folders()

        return func

    # ── Folder CRUD ───────────────────────────────────────

    def list_folders(self) -> list[FolderDefinition]:
        return sorted(self._folders.values(), key=lambda f: f.order)

    def get_folder(self, name: str) -> FolderDefinition | None:
        return self._folders.get(name)

    def create_folder(self, data: CreateFolderRequest) -> FolderDefinition | None:
        if data.name in self._folders:
            return None  # Already exists
        folder = FolderDefinition(
            name=data.name,
            description=data.description,
            order=len(self._folders),
        )
        self._folders[folder.name] = folder
        self._save_folders()
        return folder

    def rename_folder(self, name: str, data: RenameFolderRequest) -> FolderDefinition | None:
        if name not in self._folders:
            return None
        if data.new_name in self._folders and data.new_name != name:
            return None  # Target name already exists

        folder = self._folders.pop(name)
        folder.name = data.new_name
        self._folders[data.new_name] = folder

        # Update all functions in this folder
        for func in self._functions.values():
            if func.folder == name:
                func.folder = data.new_name
                self._save_function(func)

        self._save_folders()
        return folder

    def delete_folder(self, name: str) -> bool:
        if name not in self._folders:
            return False
        if name == "Uncategorized":
            return False  # Cannot delete default folder

        # Move functions to Uncategorized
        for func in self._functions.values():
            if func.folder == name:
                func.folder = "Uncategorized"
                self._save_function(func)

        del self._folders[name]
        self._save_folders()
        return True
