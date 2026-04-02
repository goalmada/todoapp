"""Google Sheets (primary) + CSV (always, as backup)."""

import csv
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _format_breakdown(breakdown: dict) -> str:
    """Format score breakdown into a readable string."""
    parts = []
    for category, (score, detail) in breakdown.items():
        parts.append(f"{category}:{score}({detail})")
    return " | ".join(parts)


def write_csv(jobs: list[dict], filename: str | None = None) -> str:
    """Write scored jobs to CSV. Returns the file path."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if filename is None:
        filename = f"jobs_{datetime.now().strftime('%Y-%m-%d')}.csv"

    filepath = os.path.join(DATA_DIR, filename)

    fieldnames = [
        "date", "score", "tier", "title", "company", "location",
        "salary_min", "salary_max", "url", "source",
        "matched_groups", "breakdown",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for job in jobs:
            writer.writerow({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "score": job.get("score", 0),
                "tier": job.get("tier", "?"),
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "salary_min": job.get("salary_min", ""),
                "salary_max": job.get("salary_max", ""),
                "url": job.get("job_url", ""),
                "source": job.get("source", ""),
                "matched_groups": ",".join(job.get("matched_groups", [])),
                "breakdown": _format_breakdown(job.get("breakdown", {})),
            })

    logger.info(f"[output] wrote {len(jobs)} jobs to {filepath}")
    return filepath


def write_sheets(jobs: list[dict]):
    """Write scored jobs to Google Sheets (requires service account setup)."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.warning("[sheets] gspread not installed. Run: pip install gspread google-auth")
        return

    creds_path = os.path.join(os.path.dirname(__file__), "config", "service_account.json")
    if not os.path.exists(creds_path):
        logger.warning(f"[sheets] no service account found at {creds_path}")
        return

    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        gc = gspread.authorize(creds)

        # Open or create spreadsheet
        sheet_name = "Job Finder — Diego"
        try:
            sh = gc.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(sheet_name)
            logger.info(f"[sheets] created new spreadsheet: {sheet_name}")

        # Create daily worksheet
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            ws = sh.add_worksheet(title=today, rows=len(jobs) + 1, cols=12)
        except gspread.exceptions.APIError:
            ws = sh.worksheet(today)
            ws.clear()

        # Write header
        header = [
            "Date", "Score", "Tier", "Title", "Company", "Location",
            "Salary Min", "Salary Max", "URL", "Source",
            "Matched Groups", "Breakdown",
        ]
        ws.append_row(header)

        # Write jobs
        for job in jobs:
            row = [
                today,
                job.get("score", 0),
                job.get("tier", "?"),
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("salary_min", ""),
                job.get("salary_max", ""),
                job.get("job_url", ""),
                job.get("source", ""),
                ",".join(job.get("matched_groups", [])),
                _format_breakdown(job.get("breakdown", {})),
            ]
            ws.append_row(row)

        # Also append to master sheet (first worksheet)
        try:
            master = sh.sheet1
            if master.title != "Master":
                master.update_title("Master")
                master.append_row(header)
            for job in jobs:
                row = [
                    today,
                    job.get("score", 0),
                    job.get("tier", "?"),
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("location", ""),
                    job.get("salary_min", ""),
                    job.get("salary_max", ""),
                    job.get("job_url", ""),
                    job.get("source", ""),
                    ",".join(job.get("matched_groups", [])),
                    _format_breakdown(job.get("breakdown", {})),
                ]
                master.append_row(row)
        except Exception as e:
            logger.warning(f"[sheets] master sheet update failed: {e}")

        logger.info(f"[sheets] wrote {len(jobs)} jobs to Google Sheets")

    except Exception as e:
        logger.error(f"[sheets] failed: {e}")
