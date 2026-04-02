"""Rule-based job scoring (max 100 points)."""

from datetime import datetime, timedelta
from profile import (
    TARGET_TITLES, TITLE_KEYWORDS, KEYWORD_GROUPS,
    REJECTED_LOCATIONS, SALARY_FLOOR, SALARY_TARGET, SALARY_STRETCH,
)


def score_title(title: str) -> tuple[int, str]:
    """Score job title match (max 30 points)."""
    title_lower = title.lower()

    # Exact target title substring match
    for target in TARGET_TITLES:
        if target in title_lower:
            return 30, f"exact:{target}"

    # Partial keyword match (2+ keywords)
    matched = [kw for kw in TITLE_KEYWORDS if kw in title_lower]
    if len(matched) >= 2:
        return 20, f"partial:{','.join(matched)}"

    # Contains at least one keyword
    if matched:
        return 10, f"weak:{','.join(matched)}"

    return 0, "no_match"


def score_description(description: str) -> tuple[int, list[str]]:
    """Score description keyword groups (max 35 points)."""
    desc_lower = description.lower()
    total = 0
    matched_groups = []

    for group_name, (weight, keywords) in KEYWORD_GROUPS.items():
        for kw in keywords:
            if kw in desc_lower:
                total += weight
                matched_groups.append(group_name)
                break  # one match per group is enough

    return min(total, 35), matched_groups


def score_remote(is_remote: bool, location: str) -> tuple[int, str]:
    """Score remote status (max 15 points)."""
    loc_lower = (location or "").lower()

    for rejected in REJECTED_LOCATIONS:
        if rejected in loc_lower:
            return -100, f"rejected:{rejected}"

    if is_remote:
        return 15, "remote"

    # Check location string for remote signals
    if any(w in loc_lower for w in ["remote", "anywhere", "worldwide"]):
        return 15, "remote_in_location"

    return 0, "not_remote"


def score_salary(salary_min: int | None, salary_max: int | None) -> tuple[int, str]:
    """Score salary range (max 15 points)."""
    if salary_min is None and salary_max is None:
        return 5, "no_data"

    # Use the higher value if available, otherwise the lower
    salary = salary_max or salary_min or 0

    # Normalize monthly to yearly if it looks monthly (< 20k)
    if 0 < salary < 20_000:
        salary = salary * 12

    if salary >= SALARY_TARGET:
        return 15, f"${salary:,}+"
    if salary >= 100_000:
        return 10, f"${salary:,}"
    if salary >= SALARY_FLOOR:
        return 5, f"${salary:,}"
    return 0, f"${salary:,}_low"


def score_recency(date_posted: str | None) -> tuple[int, str]:
    """Score how recent the posting is (max 5 points)."""
    if not date_posted:
        return 2, "no_date"

    try:
        posted = datetime.fromisoformat(date_posted.replace("Z", "+00:00"))
        now = datetime.now(posted.tzinfo) if posted.tzinfo else datetime.now()
        days_old = (now - posted).days
    except (ValueError, TypeError):
        return 2, "parse_error"

    if days_old <= 0:
        return 5, "today"
    if days_old == 1:
        return 3, "yesterday"
    if days_old <= 3:
        return 1, f"{days_old}d_ago"
    return 0, f"{days_old}d_old"


def score_job(job: dict) -> dict:
    """Score a single job. Returns the job dict with score fields added."""
    title_score, title_detail = score_title(job.get("title", ""))
    desc_score, desc_groups = score_description(job.get("description", ""))
    remote_score, remote_detail = score_remote(
        job.get("is_remote", False), job.get("location", "")
    )
    salary_score, salary_detail = score_salary(
        job.get("salary_min"), job.get("salary_max")
    )
    recency_score, recency_detail = score_recency(job.get("date_posted"))

    total = title_score + desc_score + remote_score + salary_score + recency_score

    # Determine tier
    if total >= 70:
        tier = "A"
    elif total >= 50:
        tier = "B"
    elif total >= 30:
        tier = "C"
    else:
        tier = "D"

    job["score"] = total
    job["tier"] = tier
    job["matched_groups"] = desc_groups
    job["breakdown"] = {
        "title": (title_score, title_detail),
        "description": (desc_score, desc_groups),
        "remote": (remote_score, remote_detail),
        "salary": (salary_score, salary_detail),
        "recency": (recency_score, recency_detail),
    }

    return job
