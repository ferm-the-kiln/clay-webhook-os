import asyncio
import logging
import time

import httpx

logger = logging.getLogger("clay-webhook-os")


class SumblePrefetcher:
    """Pre-fetch structured company intelligence from Sumble API.

    Returns technographic, firmographic, and hiring data as formatted markdown
    for injection into skill prompts.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.sumble.com/v3",
        cache_ttl: int = 3600,
        timeout: int = 30,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._cache_ttl = cache_ttl
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "clay-webhook-os/3.0",
            },
            timeout=timeout,
        )
        self._cache: dict[str, tuple[float, str]] = {}

    async def fetch(
        self,
        company_domain: str,
        company_name: str | None = None,
        endpoints: list[str] | None = None,
        data: dict | None = None,
    ) -> str | None:
        """Pre-fetch intelligence for a company via Sumble API.

        Args:
            company_domain: Company domain (e.g. "stripe.com").
            company_name: Company display name (for formatting).
            endpoints: Sumble endpoints to call (default: ["organizations/enrich"]).
            data: Webhook data dict — used to extract tech_stack, job_functions, etc.

        Returns:
            Formatted markdown string with structured intel, or None if all calls failed.
        """
        cache_key = company_domain.lower().strip()
        endpoints = endpoints or ["organizations/enrich"]
        data = data or {}

        # Check cache
        if cache_key in self._cache:
            ts, cached_text = self._cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                logger.info("[prefetch] Sumble cache hit for %s", cache_key)
                return cached_text

        # Call requested endpoints in parallel
        tasks = [
            self._call_endpoint(ep, self._build_payload(ep, company_domain, data))
            for ep in endpoints
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: dict[str, dict] = {}
        total_credits = 0
        for ep, res in zip(endpoints, raw_results):
            if isinstance(res, Exception):
                logger.warning("[prefetch] Sumble %s failed for %s: %s", ep, company_domain, res)
            elif res is not None:
                results[ep] = res["data"]
                total_credits += res.get("credits_used", 0)

        if not results:
            logger.warning("[prefetch] All Sumble calls failed for %s", company_domain)
            return None

        # Format results
        display_name = company_name or company_domain
        text = self._format(display_name, company_domain, results)

        # Cache result
        if len(self._cache) > 500:
            self._prune_cache()
        self._cache[cache_key] = (time.time(), text)

        logger.info(
            "[prefetch] Sumble fetched %d endpoints for %s (credits=%d)",
            len(results),
            company_domain,
            total_credits,
        )
        return text

    async def _call_endpoint(self, endpoint: str, payload: dict) -> dict | None:
        """Call a single Sumble API endpoint.

        Returns:
            {"data": <response_json>, "credits_used": <int>} or None on error.
        """
        try:
            resp = await self._client.post(f"/{endpoint}", json=payload)

            if resp.status_code == 401:
                logger.error("[prefetch] Sumble auth failed (401) — check SUMBLE_API_KEY")
                return None
            if resp.status_code == 402:
                logger.warning("[prefetch] Sumble credits exhausted (402)")
                return None
            if resp.status_code == 429:
                logger.warning("[prefetch] Sumble rate limited (429)")
                return None
            if resp.status_code >= 400:
                logger.warning("[prefetch] Sumble %s returned %d", endpoint, resp.status_code)
                return None

            body = resp.json()
            credits_used = body.get("credits_used", 0)
            return {"data": body, "credits_used": credits_used}

        except httpx.TimeoutException:
            logger.warning("[prefetch] Sumble %s timed out", endpoint)
            return None
        except Exception as e:
            logger.warning("[prefetch] Sumble %s error: %s", endpoint, e)
            return None

    # Broad default technologies for org enrichment when no specific tech_stack is provided.
    # Covers the most common enterprise stack categories to get wide coverage.
    _DEFAULT_TECHNOLOGIES = [
        "python", "java", "go", "ruby", "typescript", "react", "node.js",
        "kubernetes", "docker", "aws", "gcp", "azure", "terraform",
        "postgresql", "mongodb", "redis", "elasticsearch",
        "kafka", "spark", "snowflake", "databricks",
    ]

    def _build_payload(self, endpoint: str, domain: str, data: dict) -> dict:
        """Build request body for a Sumble endpoint based on webhook data."""
        tech_stack = data.get("tech_stack", [])
        if isinstance(tech_stack, str):
            tech_stack = [t.strip() for t in tech_stack.split(",") if t.strip()]

        if endpoint == "organizations/enrich":
            # filters.technologies is REQUIRED by the API
            technologies = tech_stack or self._DEFAULT_TECHNOLOGIES
            return {
                "organization": {"domain": domain},
                "filters": {"technologies": technologies},
            }

        if endpoint == "organizations/find":
            filters: dict = {}
            if tech_stack:
                filters["technologies"] = tech_stack
            industry = data.get("industry")
            if industry:
                filters["industry"] = industry
            return {"filters": filters, "limit": data.get("limit", 10)}

        if endpoint == "people/find":
            job_functions = data.get("job_functions", ["Engineering", "Executive"])
            if isinstance(job_functions, str):
                job_functions = [f.strip() for f in job_functions.split(",") if f.strip()]
            job_levels = data.get("job_levels", ["VP", "Director", "C-Level"])
            if isinstance(job_levels, str):
                job_levels = [l.strip() for l in job_levels.split(",") if l.strip()]
            return {
                "organization": {"domain": domain},
                "filters": {"job_functions": job_functions, "job_levels": job_levels},
                "limit": data.get("people_limit", 10),
            }

        if endpoint == "jobs/find":
            payload: dict = {
                "organization": {"domain": domain},
                "limit": data.get("jobs_limit", 10),
            }
            if tech_stack:
                payload["filters"] = {"technologies": tech_stack}
            return payload

        if endpoint == "technologies/find":
            tech_name = data.get("technology_name", "")
            return {"name": tech_name}

        # Fallback for unknown endpoints
        return {"organization": {"domain": domain}}

    def _format(self, company_name: str, domain: str, results: dict[str, dict]) -> str:
        """Convert Sumble API responses to formatted markdown."""
        parts = [
            f"# Sumble Intelligence for {company_name} ({domain})",
            "Structured company data from Sumble. Use this for technographic and firmographic analysis.\n",
        ]

        if "organizations/enrich" in results:
            parts.append(self._format_org_enrich(results["organizations/enrich"]))

        if "people/find" in results:
            parts.append(self._format_people(results["people/find"]))

        if "jobs/find" in results:
            parts.append(self._format_jobs(results["jobs/find"]))

        if "organizations/find" in results:
            parts.append(self._format_org_find(results["organizations/find"]))

        if "technologies/find" in results:
            parts.append(self._format_tech(results["technologies/find"]))

        return "\n".join(parts)

    def _format_org_enrich(self, data: dict) -> str:
        """Format organizations/enrich response.

        Actual Sumble response shape:
        {
            "organization": {"id", "slug", "name", "domain"},
            "technologies_found": "...",
            "technologies_count": N,
            "technologies": [{"name", "jobs_count", "people_count", "teams_count"}, ...]
        }
        """
        lines = ["## Technology Profile"]
        org = data.get("organization", {})

        name = org.get("name", "")
        if name:
            lines.append(f"**Company**: {name}")

        domain = org.get("domain", "")
        if domain:
            lines.append(f"**Domain**: {domain}")

        tech_count = data.get("technologies_count", 0)
        if tech_count:
            lines.append(f"**Technologies Found**: {tech_count}")

        # Technology stack table (top-level in response, not under organization)
        technologies = data.get("technologies", [])
        if technologies:
            lines.append(f"\n### Tech Stack ({len(technologies)} technologies)")
            lines.append("| Technology | Jobs | People | Teams |")
            lines.append("|-----------|------|--------|-------|")
            for tech in technologies:
                if isinstance(tech, dict):
                    t_name = tech.get("name", "")
                    jobs = tech.get("jobs_count", 0)
                    people = tech.get("people_count", 0)
                    teams = tech.get("teams_count", 0)
                    lines.append(f"| {t_name} | {jobs} | {people} | {teams} |")
                else:
                    lines.append(f"| {tech} | | | |")
        else:
            lines.append("\n*No technology data available.*")

        lines.append("")
        return "\n".join(lines)

    def _format_people(self, data: dict) -> str:
        """Format people/find response.

        Actual fields per person: id, url, linkedin_url, name, job_title,
        job_function, job_level, location, country, start_date, country_code.
        """
        people = data.get("people", [])
        lines = [f"## Key People ({len(people)} contacts)"]

        if not people:
            lines.append("*No contacts found.*\n")
            return "\n".join(lines)

        lines.append("| Name | Title | Function | Level | Location | LinkedIn |")
        lines.append("|------|-------|----------|-------|----------|----------|")
        for p in people:
            name = p.get("name", "")
            title = p.get("job_title", "") or ""
            function = p.get("job_function", "") or ""
            level = p.get("job_level", "") or ""
            location = p.get("location", "") or ""
            linkedin = p.get("linkedin_url", "") or ""
            lines.append(f"| {name} | {title} | {function} | {level} | {location} | {linkedin} |")

        lines.append("")
        return "\n".join(lines)

    def _format_jobs(self, data: dict) -> str:
        """Format jobs/find response."""
        jobs = data.get("jobs", data.get("results", []))
        lines = [f"## Recent Job Postings ({len(jobs)} jobs)"]

        if not jobs:
            lines.append("*No job postings found.*\n")
            return "\n".join(lines)

        lines.append("| Title | Location | Technologies | Posted |")
        lines.append("|-------|----------|-------------|--------|")
        for j in jobs:
            title = j.get("title", "")
            location = j.get("location", "")
            techs = j.get("technologies", [])
            tech_str = ", ".join(techs[:5]) if techs else ""
            posted = j.get("posted_date", j.get("created_at", ""))
            lines.append(f"| {title} | {location} | {tech_str} | {posted} |")

        lines.append("")
        return "\n".join(lines)

    def _format_org_find(self, data: dict) -> str:
        """Format organizations/find response.

        Actual fields per org: id, name, url, domain, industry, total_employees,
        headquarters_country, linkedin_organization_url, matching_entities.
        """
        orgs = data.get("organizations", [])
        total = data.get("total", len(orgs))
        lines = [f"## Matching Organizations ({total} total, showing {len(orgs)})"]

        if not orgs:
            lines.append("*No matching organizations found.*\n")
            return "\n".join(lines)

        lines.append("| Company | Domain | Industry | Employees | HQ |")
        lines.append("|---------|--------|----------|-----------|-----|")
        for o in orgs:
            name = o.get("name", "")
            dom = o.get("domain", "") or ""
            industry = o.get("industry", "") or ""
            emp = o.get("total_employees", "") or ""
            hq = o.get("headquarters_country", "") or ""
            lines.append(f"| {name} | {dom} | {industry} | {emp} | {hq} |")

        lines.append("")
        return "\n".join(lines)

    def _format_tech(self, data: dict) -> str:
        """Format technologies/find response."""
        tech = data.get("technology", data)
        lines = ["## Technology Lookup"]

        name = tech.get("name", "")
        slug = tech.get("slug", "")
        category = tech.get("category", "")
        lines.append(f"**Name**: {name}")
        if slug:
            lines.append(f"**Slug**: {slug}")
        if category:
            lines.append(f"**Category**: {category}")

        lines.append("")
        return "\n".join(lines)

    def _prune_cache(self):
        """Remove oldest entries when cache exceeds 500."""
        sorted_keys = sorted(self._cache, key=lambda k: self._cache[k][0])
        to_remove = sorted_keys[: len(sorted_keys) // 2]
        for key in to_remove:
            del self._cache[key]
