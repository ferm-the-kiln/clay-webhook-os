"""Table configuration validator.

Validates column dependencies, template references, conditions,
HTTP URLs, and other config before execution.
"""

import re

from app.core.url_guard import validate_url
from app.models.tables import TableColumn, TableDefinition

_TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")


def validate_table(table: TableDefinition) -> dict:
    """Validate a table's column configuration.

    Returns {"valid": bool, "errors": list[str], "warnings": list[str]}.
    """
    errors: list[str] = []
    warnings: list[str] = []

    col_ids = {c.id for c in table.columns}
    col_map = {c.id: c for c in table.columns}

    # 1. Check for duplicate column IDs
    seen_ids: set[str] = set()
    for col in table.columns:
        if col.id in seen_ids:
            errors.append(f"Duplicate column ID: '{col.id}'")
        seen_ids.add(col.id)

    # 2. Check each column
    for col in table.columns:
        prefix = f"Column '{col.name}' ({col.id})"

        # Validate column type
        valid_types = {
            "input", "enrichment", "ai", "formula", "gate", "static",
            "http", "waterfall", "lookup", "script", "write",
        }
        if col.column_type not in valid_types:
            errors.append(f"{prefix}: unknown column_type '{col.column_type}'")

        # Validate dependencies exist
        for dep_id in col.depends_on:
            if dep_id not in col_ids:
                errors.append(f"{prefix}: depends_on references unknown column '{dep_id}'")

        # Validate template references in params
        for param_name, template in col.params.items():
            for match in _TEMPLATE_RE.finditer(template):
                ref = match.group(1)
                if ref not in col_ids and ref != "env":
                    warnings.append(f"{prefix}: param '{param_name}' references unknown column '{ref}'")

        # Validate formula templates
        if col.column_type == "formula" and col.formula:
            for match in _TEMPLATE_RE.finditer(col.formula):
                ref = match.group(1)
                if ref not in col_ids:
                    warnings.append(f"{prefix}: formula references unknown column '{ref}'")

        # Validate parent-child
        if col.parent_column_id and col.parent_column_id not in col_ids:
            errors.append(f"{prefix}: parent_column_id references unknown column '{col.parent_column_id}'")

        # Validate HTTP config
        if col.column_type == "http" and col.http_config:
            cfg = col.http_config
            if not cfg.url:
                errors.append(f"{prefix}: HTTP column requires a URL")
            else:
                # Strip template vars before validating URL structure
                test_url = _TEMPLATE_RE.sub("placeholder", cfg.url)
                url_err = validate_url(test_url)
                if url_err and "placeholder" not in test_url:
                    warnings.append(f"{prefix}: URL may have issues: {url_err}")

            valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
            if cfg.method.upper() not in valid_methods:
                errors.append(f"{prefix}: invalid HTTP method '{cfg.method}'")

        # Validate waterfall config
        if col.column_type == "waterfall":
            if not col.waterfall_config or not col.waterfall_config.providers:
                errors.append(f"{prefix}: waterfall column requires at least one provider")

        # Validate lookup config
        if col.column_type == "lookup" and col.lookup_config:
            cfg = col.lookup_config
            if not cfg.source_table_id:
                errors.append(f"{prefix}: lookup requires source_table_id")
            if not cfg.match_column:
                errors.append(f"{prefix}: lookup requires match_column")
            if cfg.match_operator not in ("equals", "contains"):
                errors.append(f"{prefix}: invalid match_operator '{cfg.match_operator}'")
            if cfg.return_type not in ("value", "boolean", "count", "rows"):
                errors.append(f"{prefix}: invalid return_type '{cfg.return_type}'")

        # Validate script config
        if col.column_type == "script" and col.script_config:
            cfg = col.script_config
            if cfg.language not in ("python", "bash", "node"):
                errors.append(f"{prefix}: invalid script language '{cfg.language}'")
            if not cfg.code and not cfg.script_name:
                errors.append(f"{prefix}: script column requires either inline code or script_name")

        # Validate write config
        if col.column_type == "write" and col.write_config:
            cfg = col.write_config
            if not cfg.dest_table_id:
                errors.append(f"{prefix}: write column requires dest_table_id")
            if not cfg.column_mapping:
                errors.append(f"{prefix}: write column requires at least one column mapping")
            if cfg.mode == "upsert" and not cfg.upsert_match_key:
                errors.append(f"{prefix}: upsert mode requires upsert_match_key")

        # Validate error handling config
        if col.error_handling:
            eh = col.error_handling
            if eh.on_error not in ("skip", "fallback", "stop"):
                errors.append(f"{prefix}: invalid on_error '{eh.on_error}'")
            if eh.on_error == "fallback" and eh.fallback_value is None:
                warnings.append(f"{prefix}: on_error=fallback but no fallback_value set")
            if eh.retry_backoff not in ("exponential", "linear", "fixed"):
                errors.append(f"{prefix}: invalid retry_backoff '{eh.retry_backoff}'")

    # 3. Circular dependency detection
    cycle = _detect_circular_deps(table.columns)
    if cycle:
        errors.append(f"Circular dependency detected: {' → '.join(cycle)}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def _detect_circular_deps(columns: list[TableColumn]) -> list[str] | None:
    """Detect circular dependencies using DFS. Returns cycle path or None."""
    col_map = {c.id: c for c in columns}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {c.id: WHITE for c in columns}
    path: list[str] = []

    def dfs(node_id: str) -> list[str] | None:
        if node_id not in col_map:
            return None
        color[node_id] = GRAY
        path.append(node_id)
        for dep_id in col_map[node_id].depends_on:
            if dep_id not in color:
                continue
            if color[dep_id] == GRAY:
                # Found cycle — extract the cycle portion
                cycle_start = path.index(dep_id)
                return path[cycle_start:] + [dep_id]
            if color[dep_id] == WHITE:
                result = dfs(dep_id)
                if result:
                    return result
        path.pop()
        color[node_id] = BLACK
        return None

    for col in columns:
        if color[col.id] == WHITE:
            result = dfs(col.id)
            if result:
                return result
    return None
