"""Collects jobs from python-jobspy + Remotive API."""

import logging
import random
import time
from datetime import datetime

import requests

from profile import SEARCH_TERMS, REMOTIVE_SEARCH_TERMS

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]


def _normalize_job(raw: dict, source: str) -> dict:
    """Normalize a raw job dict to standard format."""
    return {
        "source": source,
        "title": (raw.get("title") or "").strip(),
        "company": (raw.get("company") or raw.get("company_name") or "").strip(),
        "job_url": (raw.get("job_url") or raw.get("url") or "").strip(),
        "location": (raw.get("location") or "").strip(),
        "is_remote": bool(raw.get("is_remote", False)),
        "salary_min": raw.get("min_amount") or raw.get("salary_min"),
        "salary_max": raw.get("max_amount") or raw.get("salary_max"),
        "description": (raw.get("description") or "").strip(),
        "date_posted": raw.get("date_posted") or datetime.now().isoformat(),
    }


def _sleep_between_requests():
    """Random 3-5s sleep to avoid blocking."""
    time.sleep(random.uniform(3, 5))


def scrape_jobspy(hours_old: int = 24) -> list[dict]:
    """Scrape jobs using python-jobspy library."""
    jobs = []
    try:
        from jobspy import scrape_jobs
    except ImportError:
        logger.error("python-jobspy not installed. Run: pip install python-jobspy")
        return jobs

    sites = ["indeed", "linkedin", "glassdoor", "zip_recruiter"]

    for term in SEARCH_TERMS:
        logger.info(f"[jobspy] searching: {term}")
        try:
            results = scrape_jobs(
                site_name=sites,
                search_term=term,
                location="Remote",
                is_remote=True,
                results_wanted=25,
                hours_old=hours_old,
                country_indeed="USA",
            )

            if results is not None and len(results) > 0:
                for _, row in results.iterrows():
                    raw = row.to_dict()
                    job = _normalize_job(raw, f"jobspy:{raw.get('site', 'unknown')}")
                    # jobspy uses different field names
                    job["salary_min"] = raw.get("min_amount") or raw.get("salary_min")
                    job["salary_max"] = raw.get("max_amount") or raw.get("salary_max")
                    job["is_remote"] = True  # we filtered for remote
                    if job["title"] and job["job_url"]:
                        jobs.append(job)

                logger.info(f"[jobspy] {term}: found {len(results)} results")

        except Exception as e:
            logger.warning(f"[jobspy] {term} failed: {e}")
            # One retry with backoff
            time.sleep(10)
            try:
                results = scrape_jobs(
                    site_name=sites,
                    search_term=term,
                    location="Remote",
                    is_remote=True,
                    results_wanted=25,
                    hours_old=hours_old,
                    country_indeed="USA",
                )
                if results is not None and len(results) > 0:
                    for _, row in results.iterrows():
                        raw = row.to_dict()
                        job = _normalize_job(raw, f"jobspy:{raw.get('site', 'unknown')}")
                        job["salary_min"] = raw.get("min_amount") or raw.get("salary_min")
                        job["salary_max"] = raw.get("max_amount") or raw.get("salary_max")
                        job["is_remote"] = True
                        if job["title"] and job["job_url"]:
                            jobs.append(job)
            except Exception as e2:
                logger.error(f"[jobspy] {term} retry failed: {e2}")

        _sleep_between_requests()

    logger.info(f"[jobspy] total: {len(jobs)} jobs collected")
    return jobs


def scrape_remotive() -> list[dict]:
    """Scrape jobs from Remotive API (free, no auth)."""
    jobs = []
    base_url = "https://remotive.com/api/remote-jobs"

    for term in REMOTIVE_SEARCH_TERMS:
        logger.info(f"[remotive] searching: {term}")
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            resp = requests.get(
                base_url,
                params={"category": "software-dev", "search": term},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for raw in data.get("jobs", []):
                job = {
                    "source": "remotive",
                    "title": (raw.get("title") or "").strip(),
                    "company": (raw.get("company_name") or "").strip(),
                    "job_url": (raw.get("url") or "").strip(),
                    "location": (raw.get("candidate_required_location") or "").strip(),
                    "is_remote": True,  # remotive is all remote
                    "salary_min": None,
                    "salary_max": None,
                    "description": (raw.get("description") or "").strip(),
                    "date_posted": raw.get("publication_date") or datetime.now().isoformat(),
                }
                # Parse salary from tags if available
                salary_str = raw.get("salary") or ""
                if salary_str:
                    job["salary_raw"] = salary_str

                if job["title"] and job["job_url"]:
                    jobs.append(job)

            logger.info(f"[remotive] {term}: found {len(data.get('jobs', []))} results")

        except Exception as e:
            logger.warning(f"[remotive] {term} failed: {e}")
            time.sleep(10)
            try:
                resp = requests.get(
                    base_url,
                    params={"category": "software-dev", "search": term},
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                for raw in data.get("jobs", []):
                    job = {
                        "source": "remotive",
                        "title": (raw.get("title") or "").strip(),
                        "company": (raw.get("company_name") or "").strip(),
                        "job_url": (raw.get("url") or "").strip(),
                        "location": (raw.get("candidate_required_location") or "").strip(),
                        "is_remote": True,
                        "salary_min": None,
                        "salary_max": None,
                        "description": (raw.get("description") or "").strip(),
                        "date_posted": raw.get("publication_date") or datetime.now().isoformat(),
                    }
                    if job["title"] and job["job_url"]:
                        jobs.append(job)
            except Exception as e2:
                logger.error(f"[remotive] {term} retry failed: {e2}")

        _sleep_between_requests()

    logger.info(f"[remotive] total: {len(jobs)} jobs collected")
    return jobs


def scrape_all(hours_old: int = 24) -> list[dict]:
    """Run all scrapers and combine results."""
    all_jobs = []

    # Remotive first (lighter, less likely to block)
    all_jobs.extend(scrape_remotive())

    # python-jobspy (heavier, may get blocked)
    all_jobs.extend(scrape_jobspy(hours_old=hours_old))

    logger.info(f"[scraper] total across all sources: {len(all_jobs)} jobs")
    return all_jobs
