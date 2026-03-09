import logging

logger = logging.getLogger("clay-webhook-os")


def group_by_company(rows: list[dict]) -> dict[str, list[dict]]:
    """Group rows by normalized company_domain.

    Rows without a company_domain are grouped under the empty string key.
    Returns {domain: [rows]} preserving original row order within each group.
    """
    groups: dict[str, list[dict]] = {}
    for row in rows:
        domain = (row.get("company_domain") or "").lower().strip()
        groups.setdefault(domain, []).append(row)

    company_count = sum(1 for k in groups if k)
    ungrouped = len(groups.get("", []))
    logger.info(
        "[batch-optimizer] Grouped %d rows into %d companies (%d ungrouped)",
        len(rows), company_count, ungrouped,
    )
    return groups
