"""Adapter interfaces for the live data sources.

These are deliberately thin Protocols so the existing soccer APIs can be wired
in without the engine knowing any vendor specifics. Implement each Protocol with
a concrete adapter (endpoint + auth) and pass instances to ``LivePipeline``.

The pipeline overlays *live* data on top of the *static* seed profiles:
- the latest FIFA ranking refreshes ``fifa_rank`` / ``fifa_points``;
- the live match feed drives the ``MatchState`` clock (minute, added time,
  extra time, score, phase);
- the lineup feed can mark which key players actually started.

Nothing here makes network calls yet — concrete adapters fill that in once the
API endpoints/credentials are provided.
"""

from __future__ import annotations

from typing import Optional, Protocol

from ..schema import MatchState, TeamProfile, PredictionContext
from ..context_builder import load_profile


class RankingSource(Protocol):
    """Latest FIFA World Ranking position/points for a team."""

    def get_rank(self, iso3: str) -> tuple[Optional[int], Optional[float]]:
        """Return ``(fifa_rank, fifa_points)`` for the team."""
        ...


class MatchStateSource(Protocol):
    """Live match clock + scoreline for a fixture."""

    def get_match_state(self, fixture_id: str) -> MatchState:
        ...


class LineupSource(Protocol):
    """Confirmed starting lineup for a team in a fixture (optional)."""

    def get_starters(self, fixture_id: str, iso3: str) -> list[str]:
        """Return the names of confirmed starters."""
        ...


class LivePipeline:
    """Builds a live PredictionContext by overlaying feeds on seed profiles."""

    def __init__(
        self,
        ranking_source: Optional[RankingSource] = None,
        match_state_source: Optional[MatchStateSource] = None,
        lineup_source: Optional[LineupSource] = None,
    ) -> None:
        self.ranking_source = ranking_source
        self.match_state_source = match_state_source
        self.lineup_source = lineup_source

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
