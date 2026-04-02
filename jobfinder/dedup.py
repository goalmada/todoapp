"""JSON-based dedup store across runs."""

import json
import logging
import os
from datetime import datetime
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

SEEN_JOBS_PATH = os.path.join(os.path.dirname(__file__), "data", "seen_jobs.json")


def _normalize_url(url: str) -> str:
    """Strip query params and fragments for dedup comparison."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _load_seen() -> dict:
    """Load the seen jobs store."""
    if os.path.exists(SEEN_JOBS_PATH):
        try:
            with open(SEEN_JOBS_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("corrupted seen_jobs.json, starting fresh")
    return {}


def _save_seen(seen: dict):
    """Save the seen jobs store."""
    os.makedirs(os.path.dirname(SEEN_JOBS_PATH), exist_ok=True)
    with open(SEEN_JOBS_PATH, "w") as f:
        json.dump(seen, f, indent=2)


def dedup_jobs(jobs: list[dict]) -> list[dict]:
    """Deduplicate jobs within-run and across-runs.

    Returns only new, unique jobs.
    """
    seen = _load_seen()
    today = datetime.now().strftime("%Y-%m-%d")

    # Within-run dedup by normalized URL
    url_seen = {}
    # Secondary dedup by (company, title) tuple
    title_seen = {}
    new_jobs = []

    for job in jobs:
        url = _normalize_url(job.get("job_url", ""))

        # Skip if no URL
        if not url or url in ("", "https://", "http://"):
            continue

        # Cross-run dedup: skip if we've seen this URL before
        if url in seen:
            continue

        # Within-run URL dedup
        if url in url_seen:
            continue

        # Secondary dedup: (company, title) — keep the one with longer description
        key = (
            job.get("company", "").lower().strip(),
            job.get("title", "").lower().strip(),
        )
        if key[0] and key[1] and key in title_seen:
            existing_idx = title_seen[key]
            existing = new_jobs[existing_idx]
            if len(job.get("description", "")) > len(existing.get("description", "")):
                new_jobs[existing_idx] = job
                url_seen[_normalize_url(existing.get("job_url", ""))] = False
                url_seen[url] = True
            continue

        url_seen[url] = True
        title_seen[key] = len(new_jobs)
        new_jobs.append(job)

    # Mark all new jobs as seen for next run
    for job in new_jobs:
        url = _normalize_url(job.get("job_url", ""))
        if url:
            seen[url] = today

    _save_seen(seen)
    logger.info(f"[dedup] {len(jobs)} in -> {len(new_jobs)} new (filtered {len(jobs) - len(new_jobs)} dupes)")
    return new_jobs
