"""Table source executor — auto-populate tables from external data.

Supports HTTP, webhook, and script source types.
"""

import json
import logging
import uuid

import aiohttp

from app.core.table_store import TableStore
from app.core.url_guard import validate_url

logger = logging.getLogger("clay-webhook-os")


async def execute_http_source(
    source_config: dict,
    table_store: TableStore,
    table_id: str,
) -> dict:
    """Fetch data from an HTTP endpoint and import into table.

    source_config fields:
      url, method, headers, body, extract (JSONPath), column_mapping,
      dedup_column, update_existing
    """
    url = source_config.get("url", "")
    method = source_config.get("method", "GET")
    headers = source_config.get("headers", {})
    body = source_config.get("body")
    extract = source_config.get("extract", "$")
    column_mapping = source_config.get("column_mapping", {})
    dedup_column = source_config.get("dedup_column")
    update_existing = source_config.get("update_existing", False)

    # Validate URL
    url_err = validate_url(url)
    if url_err:
        return {"error": True, "message": f"SSRF blocked: {url_err}"}

    # Fetch data
    req_headers = dict(headers)
    req_body = None
    if body:
        req_body = json.dumps(body).encode() if isinstance(body, dict) else str(body).encode()
        req_headers.setdefault("Content-Type", "application/json")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method.upper(), url=url, headers=req_headers,
                data=req_body, timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    return {"error": True, "message": f"HTTP {resp.status}: {text[:200]}"}
                data = await resp.json(content_type=None)
    except Exception as e:
        return {"error": True, "message": str(e)}

    # Extract array from response
    from app.core.table_executor import _jsonpath_extract
    items = _jsonpath_extract(data, extract)
    if not isinstance(items, list):
        items = [items] if items is not None else []

    # Map columns and build rows
    rows = _map_items_to_rows(items, column_mapping)

    # Dedup + import
    if dedup_column and update_existing:
        result = table_store.upsert_rows(table_id, rows, dedup_column)
    elif dedup_column:
        # Dedup only — skip existing
        existing_rows, _ = table_store.get_rows(table_id, offset=0, limit=100_000)
        existing_vals = {str(r.get(f"{dedup_column}__value", "")) for r in existing_rows}
        new_rows = [r for r in rows if str(r.get(f"{dedup_column}__value", "")) not in existing_vals]
        count = table_store.import_rows(table_id, new_rows)
        result = {"inserted": count, "skipped": len(rows) - count}
    else:
        count = table_store.import_rows(table_id, rows)
        result = {"inserted": count}

    logger.info("[source_executor] HTTP source imported %s rows into %s", len(rows), table_id)
    return {"ok": True, "source_type": "http", "items_fetched": len(items), **result}


async def execute_script_source(
    source_config: dict,
    table_store: TableStore,
    table_id: str,
) -> dict:
    """Run a script and import JSON array output into table."""
    from app.core.script_executor import execute_script

    script_name = source_config.get("script_name", "")
    code = source_config.get("code", "")
    language = source_config.get("language", "python")
    column_mapping = source_config.get("column_mapping", {})
    dedup_column = source_config.get("dedup_column")

    if not code and not script_name:
        return {"error": True, "message": "No script code or script_name provided"}

    try:
        result = await execute_script(code=code, language=language, row_data={}, timeout=60)
    except Exception as e:
        return {"error": True, "message": str(e)}

    items = result if isinstance(result, list) else [result] if result else []
    rows = _map_items_to_rows(items, column_mapping)

    if dedup_column:
        result_info = table_store.upsert_rows(table_id, rows, dedup_column)
    else:
        count = table_store.import_rows(table_id, rows)
        result_info = {"inserted": count}

    return {"ok": True, "source_type": "script", "items_fetched": len(items), **result_info}


def execute_webhook_source(
    payload: dict | list,
    source_config: dict,
    table_store: TableStore,
    table_id: str,
) -> dict:
    """Process webhook payload and import into table."""
    column_mapping = source_config.get("column_mapping", {})
    dedup_column = source_config.get("dedup_column")
    update_existing = source_config.get("update_existing", False)

    items = payload if isinstance(payload, list) else [payload]
    rows = _map_items_to_rows(items, column_mapping)

    if dedup_column and update_existing:
        result = table_store.upsert_rows(table_id, rows, dedup_column)
    else:
        count = table_store.import_rows(table_id, rows)
        result = {"inserted": count}

    return {"ok": True, "source_type": "webhook", "items_received": len(items), **result}


def _map_items_to_rows(items: list, column_mapping: dict[str, str]) -> list[dict]:
    """Map source items to table rows using column mapping.

    column_mapping: { "table_column_id": "$.source.field" }
    If no mapping, pass items through as-is.
    """
    if not column_mapping:
        # No mapping — use items as-is, adding row IDs
        rows = []
        for item in items:
            row = {"_row_id": uuid.uuid4().hex[:12]}
            if isinstance(item, dict):
                for k, v in item.items():
                    row[f"{k}__value"] = v
                    row[f"{k}__status"] = "done"
            rows.append(row)
        return rows

    from app.core.table_executor import _jsonpath_extract

    rows = []
    for item in items:
        row = {"_row_id": uuid.uuid4().hex[:12]}
        for col_id, path in column_mapping.items():
            if path.startswith("$"):
                val = _jsonpath_extract(item, path)
            elif isinstance(item, dict):
                val = item.get(path)
            else:
                val = None
            row[f"{col_id}__value"] = val
            row[f"{col_id}__status"] = "done"
        rows.append(row)
    return rows
