"""Google Sheets bidirectional adapter for tables.

Enables tables to sync to/from Google Sheets.
Sheets is an optional view, not the source of truth.
"""

import json
import logging
import time
import uuid

from app.core.sheets_client import SheetsClient
from app.core.table_store import TableStore
from app.models.tables import TableDefinition

logger = logging.getLogger("clay-webhook-os")


class SheetsAdapter:
    """Bridge between TableStore and Google Sheets."""

    def __init__(self, sheets_client: SheetsClient, table_store: TableStore):
        self._sheets = sheets_client
        self._tables = table_store

    @property
    def available(self) -> bool:
        return self._sheets.available

    async def import_from_sheet(self, spreadsheet_id: str, table_id: str, range_: str = "Sheet1") -> dict:
        """Pull rows from a Google Sheet into a table.

        First row is treated as headers. Maps headers to table column IDs.
        Returns {imported: int, columns_mapped: int}.
        """
        if not self._sheets.available:
            return {"error": True, "message": "Google Sheets not available (gws CLI not installed)"}

        values = await self._sheets.read_values(spreadsheet_id, range_)
        if not values or len(values) < 2:
            return {"imported": 0, "columns_mapped": 0, "message": "Sheet is empty or has only headers"}

        headers = values[0]
        data_rows = values[1:]

        table = self._tables.get(table_id)
        if not table:
            return {"error": True, "message": "Table not found"}

        # Build column mapping: header → column ID
        col_by_name = {c.name.lower(): c.id for c in table.columns}
        col_by_id = {c.id: c.id for c in table.columns}
        mapping: dict[int, str] = {}
        for i, header in enumerate(headers):
            h = header.strip()
            col_id = col_by_id.get(h) or col_by_name.get(h.lower())
            if col_id:
                mapping[i] = col_id

        # Build rows
        rows = []
        for data_row in data_rows:
            row = {"_row_id": uuid.uuid4().hex[:12]}
            for col_idx, col_id in mapping.items():
                val = data_row[col_idx] if col_idx < len(data_row) else ""
                row[f"{col_id}__value"] = val
                row[f"{col_id}__status"] = "done"
            rows.append(row)

        count = self._tables.import_rows(table_id, rows)
        logger.info("[sheets_adapter] Imported %d rows from sheet %s into table %s", count, spreadsheet_id, table_id)
        return {"imported": count, "columns_mapped": len(mapping)}

    async def export_to_sheet(self, table_id: str, spreadsheet_id: str, range_: str = "Sheet1") -> dict:
        """Push table rows to a Google Sheet.

        Writes headers from column names, then all row values.
        Returns {exported: int}.
        """
        if not self._sheets.available:
            return {"error": True, "message": "Google Sheets not available (gws CLI not installed)"}

        table = self._tables.get(table_id)
        if not table:
            return {"error": True, "message": "Table not found"}

        rows, _ = self._tables.get_rows(table_id, offset=0, limit=100_000)

        # Build headers from column definitions
        columns = sorted(table.columns, key=lambda c: c.position)
        headers = [c.name for c in columns]
        col_ids = [c.id for c in columns]

        # Build value rows
        sheet_rows = [headers]
        for row in rows:
            sheet_row = []
            for col_id in col_ids:
                val = row.get(f"{col_id}__value", "")
                if isinstance(val, dict | list):
                    sheet_row.append(json.dumps(val))
                elif val is None:
                    sheet_row.append("")
                else:
                    sheet_row.append(str(val))
            sheet_rows.append(sheet_row)

        await self._sheets.write_values(spreadsheet_id, range_, sheet_rows)
        logger.info("[sheets_adapter] Exported %d rows from table %s to sheet %s", len(rows), table_id, spreadsheet_id)
        return {"exported": len(rows)}

    async def sync(self, table_id: str, spreadsheet_id: str, direction: str = "push") -> dict:
        """Sync table ↔ sheet.

        direction: pull | push | both
        """
        results = {}
        if direction in ("pull", "both"):
            results["pull"] = await self.import_from_sheet(spreadsheet_id, table_id)
        if direction in ("push", "both"):
            results["push"] = await self.export_to_sheet(table_id, spreadsheet_id)
        return results
