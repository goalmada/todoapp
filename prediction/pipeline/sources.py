"""Adapter interfaces and concrete implementations for live data sources.

Protocol interfaces let the engine stay vendor-agnostic. Concrete adapters
for API-Football (api-sports.io, Pro plan) are included below.

Rate limits (Pro plan): 300 req/min, 7500 req/day.
Data latency: API-Football updates live scores every ~15s from their data
providers. Combined with our polling interval, realistic goal-detection
latency is 15-30s (see ApiFootballMatchStateSource docstring).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, Protocol

from ..schema import (
    GoalEvent,
    GroupStanding,
    MatchState,
    Phase,
    TeamProfile,
    PredictionContext,
)
from ..context_builder import load_profile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Protocol interfaces
# ---------------------------------------------------------------------------


class RankingSource(Protocol):
    """Latest FIFA World Ranking position/points for a team."""

    def get_rank(self, iso3: str) -> tuple[Optional[int], Optional[float]]:
        """Return ``(fifa_rank, fifa_points)`` for the team."""
        ...


class MatchStateSource(Protocol):
    """Live match clock + scoreline + goal events for a fixture."""

    def get_match_state(self, fixture_id: str) -> MatchState:
        ...


class LineupSource(Protocol):
    """Confirmed starting lineup for a team in a fixture (optional)."""

    def get_starters(self, fixture_id: str, iso3: str) -> list[str]:
        """Return the names of confirmed starters."""
        ...


class StandingsSource(Protocol):
    """Tournament group standings (points, W/L/D, goal diff)."""

    def get_group_standings(self) -> list[GroupStanding]:
        """Return all group standings for the tournament."""
        ...

    def get_team_standing(self, team_name: str) -> Optional[GroupStanding]:
        """Return standing for a specific team, or None."""
        ...


# ---------------------------------------------------------------------------
# API-Football helpers
# ---------------------------------------------------------------------------

_STATUS_TO_PHASE = {
    "TBD": Phase.PRE_MATCH,
    "NS": Phase.PRE_MATCH,
    "1H": Phase.FIRST_HALF,
    "HT": Phase.HALF_TIME,
    "2H": Phase.SECOND_HALF,
    "ET": Phase.EXTRA_FIRST,
    "BT": Phase.EXTRA_HALF_TIME,
    "P": Phase.PENALTIES,
    "FT": Phase.FULL_TIME,
    "AET": Phase.FULL_TIME,
    "PEN": Phase.FULL_TIME,
    "SUSP": Phase.PRE_MATCH,
    "INT": Phase.HALF_TIME,
    "PST": Phase.PRE_MATCH,
    "CANC": Phase.FULL_TIME,
    "ABD": Phase.FULL_TIME,
    "AWD": Phase.FULL_TIME,
    "WO": Phase.FULL_TIME,
    "LIVE": Phase.FIRST_HALF,
}


def _get_api_football_key() -> Optional[str]:
    """Resolve the API-Football key from env or AWS Secrets Manager."""
    key = os.environ.get("API_FOOTBALL_KEY")
    if key:
        return key
    try:
        profile = os.environ.get("AWS_PROFILE", "cb-admin")
        region = os.environ.get("AWS_REGION", "us-east-1")
        cmd = [
            "aws", "secretsmanager", "get-secret-value",
            "--secret-id", "cost-dashboard-api-keys-prod",
            "--profile", profile,
            "--region", region,
            "--query", "SecretString",
            "--output", "text",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning("Failed to fetch API key from Secrets Manager: %s", result.stderr.strip())
            return None
        secrets = json.loads(result.stdout)
        return secrets.get("api_football_key")
    except Exception as e:
        logger.warning("Error fetching API-Football key: %s", e)
        return None


def _api_football_request(endpoint: str, params: dict, api_key: str) -> Optional[dict]:
    """Make a request to the API-Football v3 endpoint."""
    url = f"https://v3.football.api-sports.io/{endpoint}"
    param_str = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{param_str}" if params else url
    try:
        cmd = ["curl", "-s", full_url, "-H", f"x-apisports-key: {api_key}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning("API-Football curl failed: %s", result.stderr.strip())
            return None
        data = json.loads(result.stdout)
        errors = data.get("errors")
        if errors and (isinstance(errors, dict) and any(errors.values()) or isinstance(errors, list) and errors):
            logger.warning("API-Football errors on %s: %s", endpoint, errors)
            return None
        return data
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        logger.warning("API-Football request error for %s: %s", endpoint, e)
        return None


# ---------------------------------------------------------------------------
# Concrete adapters: API-Football
# ---------------------------------------------------------------------------

WC_LEAGUE_ID = 1
WC_SEASON = 2026


@dataclass
class ApiFootballMatchStateSource:
    """Live match state from API-Football.

    Polling strategy (Pro plan, 300 req/min):
    - During live WC matches: poll every 15s (4 req/min per match).
      API-Football's data providers update scores roughly every 15s.
      Polling faster than 15s wastes quota without gaining latency.
    - Realistic goal-detection latency: 15-30s after the real goal.
      The API's upstream data feed (Opta/Stats Perform) typically
      reflects a goal within 10-20s; our 15s poll adds 0-15s on top.
    - This is significantly faster than ESPN's 60s+ polling.
    - Sub-10s detection is NOT reliably achievable with any REST-polling
      API. True sub-5s requires a push/WebSocket feed (not available
      from API-Football on Pro plan).
    """

    api_key: str = ""

    def __post_init__(self):
        if not self.api_key:
            self.api_key = _get_api_football_key() or ""

    def get_match_state(self, fixture_id: str) -> MatchState:
        if not self.api_key:
            logger.warning("No API-Football key available, returning default MatchState")
            return MatchState()

        data = _api_football_request("fixtures", {"id": fixture_id}, self.api_key)
        if not data or not data.get("response"):
            return MatchState()

        fix = data["response"][0]
        status = fix["fixture"]["status"]
        phase = _STATUS_TO_PHASE.get(status["short"], Phase.PRE_MATCH)
        minute = status.get("elapsed") or 0
        extra = status.get("extra")

        goals_home = fix.get("goals", {}).get("home") or 0
        goals_away = fix.get("goals", {}).get("away") or 0

        round_str = fix.get("league", {}).get("round", "")
        is_knockout = "Group" not in round_str and minute > 0

        goal_events = self._fetch_goal_events(fixture_id)

        return MatchState(
            phase=phase,
            minute=minute,
            added_time=extra,
            home_score=goals_home,
            away_score=goals_away,
            is_knockout=is_knockout,
            goals=goal_events,
        )

    def _fetch_goal_events(self, fixture_id: str) -> list[GoalEvent]:
        data = _api_football_request("fixtures/events", {"fixture": fixture_id}, self.api_key)
        if not data or not data.get("response"):
            return []

        goals = []
        for event in data["response"]:
            if event.get("type") != "Goal":
                continue
            goals.append(GoalEvent(
                minute=event["time"]["elapsed"],
                team=event["team"]["name"],
                player=event["player"]["name"] or "Unknown",
                assist=event.get("assist", {}).get("name") or "",
                detail=event.get("detail", ""),
            ))
        return goals


@dataclass
class ApiFootballLineupSource:
    """Lineups from API-Football. Available ~30-60 min before kickoff."""

    api_key: str = ""

    def __post_init__(self):
        if not self.api_key:
            self.api_key = _get_api_football_key() or ""

    def get_starters(self, fixture_id: str, iso3: str) -> list[str]:
        if not self.api_key:
            return []

        data = _api_football_request("fixtures/lineups", {"fixture": fixture_id}, self.api_key)
        if not data or not data.get("response"):
            return []

        for team_lineup in data["response"]:
            team_name = team_lineup["team"]["name"].lower()
            if iso3.lower() in team_name or team_name in iso3.lower():
                starters = team_lineup.get("startXI", [])
                return [p["player"]["name"] for p in starters if p.get("player", {}).get("name")]

        return []


@dataclass
class ApiFootballStandingsSource:
    """World Cup group standings from API-Football."""

    api_key: str = ""
    _cache: Optional[list[GroupStanding]] = None
    _cache_ts: float = 0.0
    _cache_ttl: float = 300.0  # 5 min cache

    def __post_init__(self):
        if not self.api_key:
            self.api_key = _get_api_football_key() or ""

    def _refresh_if_stale(self) -> list[GroupStanding]:
        now = time.time()
        if self._cache is not None and (now - self._cache_ts) < self._cache_ttl:
            return self._cache

        if not self.api_key:
            return []

        data = _api_football_request(
            "standings", {"league": str(WC_LEAGUE_ID), "season": str(WC_SEASON)}, self.api_key,
        )
        if not data or not data.get("response"):
            return self._cache or []

        standings = []
        for group in data["response"][0]["league"]["standings"]:
            for entry in group:
                all_stats = entry.get("all", {})
                standings.append(GroupStanding(
                    team=entry["team"]["name"],
                    team_id=entry["team"]["id"],
                    group=entry.get("group", ""),
                    rank=entry.get("rank", 0),
                    played=all_stats.get("played", 0),
                    won=all_stats.get("win", 0),
                    drawn=all_stats.get("draw", 0),
                    lost=all_stats.get("lose", 0),
                    goals_for=all_stats.get("goals", {}).get("for", 0),
                    goals_against=all_stats.get("goals", {}).get("against", 0),
                    goal_diff=entry.get("goalsDiff", 0),
                    points=entry.get("points", 0),
                    form=entry.get("form", ""),
                ))

        self._cache = standings
        self._cache_ts = now
        return standings

    def get_group_standings(self) -> list[GroupStanding]:
        return self._refresh_if_stale()

    def get_team_standing(self, team_name: str) -> Optional[GroupStanding]:
        for s in self._refresh_if_stale():
            if s.team.lower() == team_name.lower():
                return s
        return None


# ---------------------------------------------------------------------------
# LivePipeline (orchestrates all sources)
# ---------------------------------------------------------------------------


class LivePipeline:
    """Builds a live PredictionContext by overlaying feeds on seed profiles."""

    def __init__(
        self,
        ranking_source: Optional[RankingSource] = None,
        match_state_source: Optional[MatchStateSource] = None,
        lineup_source: Optional[LineupSource] = None,
        standings_source: Optional[StandingsSource] = None,
    ) -> None:
        self.ranking_source = ranking_source
        self.match_state_source = match_state_source
        self.lineup_source = lineup_source
        self.standings_source = standings_source

    def _refresh_ranking(self, profile: TeamProfile) -> TeamProfile:
        if self.ranking_source is None:
            return profile
        rank, points = self.ranking_source.get_rank(profile.iso3)
        if rank is not None:
            profile.fifa_rank = rank
        if points is not None:
            profile.fifa_points = points
        return profile

    def build_live_context(
        self, fixture_id: str, home_iso3: str, away_iso3: str
    ) -> PredictionContext:
        home = self._refresh_ranking(load_profile(home_iso3))
        away = self._refresh_ranking(load_profile(away_iso3))

        if self.match_state_source is not None:
            match_state = self.match_state_source.get_match_state(fixture_id)
        else:
            match_state = MatchState()

        return PredictionContext(home=home, away=away, match_state=match_state)

    @classmethod
    def from_api_football(cls, api_key: str = "") -> "LivePipeline":
        """Convenience factory: wire all three API-Football sources."""
        return cls(
            match_state_source=ApiFootballMatchStateSource(api_key=api_key),
            lineup_source=ApiFootballLineupSource(api_key=api_key),
            standings_source=ApiFootballStandingsSource(api_key=api_key),
        )
