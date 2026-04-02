#!/usr/bin/env python3
"""Job Finder — find remote AI roles that match Diego's profile."""

import argparse
import logging
import sys

from scraper import scrape_all
from scorer import score_job
from dedup import dedup_jobs
from output import write_csv, write_sheets


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(description="Find remote AI jobs matching your profile")
    parser.add_argument("--hours", type=int, default=24, help="How many hours back to search (default: 24)")
    parser.add_argument("--csv-only", action="store_true", help="Skip Google Sheets, only write CSV")
    parser.add_argument("--min-score", type=int, default=0, help="Minimum score to include (default: 0)")
    parser.add_argument("--dry-run", action="store_true", help="Scrape and score but don't write output")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # 1. Scrape
    logger.info(f"scraping jobs from last {args.hours} hours...")
    raw_jobs = scrape_all(hours_old=args.hours)

    if not raw_jobs:
        logger.warning("no jobs found from any source")
        sys.exit(0)

    # 2. Dedup
    logger.info("deduplicating...")
    unique_jobs = dedup_jobs(raw_jobs)

    if not unique_jobs:
        logger.info("no new jobs after dedup")
        sys.exit(0)

    # 3. Score
    logger.info("scoring...")
    scored_jobs = [score_job(job) for job in unique_jobs]

    # Filter by min score
    if args.min_score > 0:
        scored_jobs = [j for j in scored_jobs if j["score"] >= args.min_score]
        logger.info(f"filtered to {len(scored_jobs)} jobs with score >= {args.min_score}")

    # Sort by score descending
    scored_jobs.sort(key=lambda j: j["score"], reverse=True)

    # 4. Summary
    tiers = {"A": 0, "B": 0, "C": 0, "D": 0}
    for job in scored_jobs:
        tiers[job["tier"]] = tiers.get(job["tier"], 0) + 1

    logger.info(f"results: {len(scored_jobs)} jobs — A:{tiers['A']} B:{tiers['B']} C:{tiers['C']} D:{tiers['D']}")

    # Print top 10
    print(f"\n{'='*80}")
    print(f"TOP MATCHES ({len(scored_jobs)} total)")
    print(f"{'='*80}")
    for i, job in enumerate(scored_jobs[:10], 1):
        salary = ""
        if job.get("salary_min") or job.get("salary_max"):
            sal_min = f"${job['salary_min']:,}" if job.get("salary_min") else "?"
            sal_max = f"${job['salary_max']:,}" if job.get("salary_max") else "?"
            salary = f" | {sal_min}-{sal_max}"
        print(f"\n{i}. [{job['tier']}] {job['score']}pts — {job['title']}")
        print(f"   {job['company']} | {job['source']}{salary}")
        print(f"   {job['job_url']}")
        print(f"   groups: {', '.join(job.get('matched_groups', []))}")

    if args.dry_run:
        logger.info("dry run — skipping output")
        return

    # 5. Output
    csv_path = write_csv(scored_jobs)
    print(f"\nCSV saved: {csv_path}")

    if not args.csv_only:
        write_sheets(scored_jobs)


if __name__ == "__main__":
    main()
