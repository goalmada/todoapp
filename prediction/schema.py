"""Data contracts for the prediction context bundle.

These dataclasses mirror the JSON schema documented in
``docs/soccer_prediction_scope.md`` (§2 and §4). They are deliberately
dependency-free so both the deterministic model and the LLM adjuster can
consume them without importing each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Phase(str, Enum):
    """Where the match clock currently is."""

    PRE_MATCH = "PRE_MATCH"
    FIRST_HALF = "FIRST_HALF"
    HALF_TIME = "HALF_TIME"
    SECOND_HALF = "SECOND_HALF"
    EXTRA_FIRST = "EXTRA_FIRST"
    EXTRA_HALF_TIME = "EXTRA_HALF_TIME"
    EXTRA_SECOND = "EXTRA_SECOND"
    PENALTIES = "PENALTIES"
    FULL_TIME = "FULL_TIME"


@dataclass
class KeyPlayer:
    name: str
    position: str = ""
    role: str = ""
    note: str = ""


@dataclass
class MediaSentiment:
    label: str = "neutral"  # positive | neutral | negative
    confidence: float = 0.0
    summary: str = ""


@dataclass
class TeamProfile:
    """Static, research-sourced profile for one national team (seed data)."""

    team: str
    iso3: str
    fifa_rank: Optional[int] = None
    fifa_points: Optional[float] = None
    as_of: Optional[str] = None
    style: str = ""
    recent_form: str = ""
    strength_index: Optional[float] = None  # 0..100
    key_players: list[KeyPlayer] = field(default_factory=list)
    historical_news: list[str] = field(default_factory=list)
    media_sentiment: MediaSentiment = field(default_factory=MediaSentiment)
    sources: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "TeamProfile":
        players = [KeyPlayer(**p) for p in d.get("key_players", [])]
        sentiment = MediaSentiment(**d.get("media_sentiment", {}))
        known = {
            "team", "iso3", "fifa_rank", "fifa_points", "as_of", "style",
            "recent_form", "strength_index", "historical_news", "sources",
        }
        base = {k: d[k] for k in known if k in d}
        return cls(key_players=players, media_sentiment=sentiment, **base)


@dataclass
class MatchState:
    """Live clock + scoreline. The time-awareness core of the system.

    Group-stage matches end at 90' (+added time) and a draw is terminal.
    Knockout matches with a level score roll into 30' of extra time and then
    penalties, so ``is_knockout`` changes how much football is left to play.
    """

    phase: Phase = Phase.PRE_MATCH
    minute: int = 0
    added_time: Optional[int] = None
    home_score: int = 0
    away_score: int = 0
    is_knockout: bool = False

    # ----- derived clock helpers -----
    @property
    def regulation_minutes_remaining(self) -> float:
        """Minutes left in the 90' regulation period, including added time."""
        if self.phase in (Phase.PRE_MATCH, Phase.FIRST_HALF, Phase.HALF_TIME,
                           Phase.SECOND_HALF):
            full = 90 + (self.added_time or 0)
            return max(0.0, full - self.minute)
        return 0.0

    @property
    def extra_time_minutes_remaining(self) -> float:
        """Minutes left in the 30' extra-time period, including added time."""
        if self.phase in (Phase.EXTRA_FIRST, Phase.EXTRA_HALF_TIME,
                           Phase.EXTRA_SECOND):
            full = 120 + (self.added_time or 0)
            return max(0.0, full - self.minute)
        return 0.0

    @property
    def minutes_remaining(self) -> float:
        """Total live football minutes expected to remain before resolution."""
        if self.phase == Phase.PRE_MATCH:
            # Knockout games may need ET, but we price that via draw roll-over,
            # not extra clock here.
            return 90.0
        return self.regulation_minutes_remaining + self.extra_time_minutes_remaining

    @property
    def is_finished(self) -> bool:
        return self.phase in (Phase.FULL_TIME, Phase.PENALTIES)


@dataclass
class PredictionContext:
    """The full context bundle injected into the engine."""

    home: TeamProfile
    away: TeamProfile
    match_state: MatchState

    def rank_gap(self) -> Optional[int]:
        if self.home.fifa_rank is None or self.away.fifa_rank is None:
            return None
        # Positive => home is better ranked (lower number).
        return self.away.fifa_rank - self.home.fifa_rank

    def points_gap(self) -> Optional[float]:
        if self.home.fifa_points is None or self.away.fifa_points is None:
            return None
        return self.home.fifa_points - self.away.fifa_points


@dataclass
class Prediction:
    """Engine output. Carries both baseline and final for auditability."""

    home_win: float
    draw: float
    away_win: float
    source: str = "deterministic"  # "deterministic" | "hybrid"
    rationale: str = ""
    baseline: Optional["Prediction"] = None

    def as_dict(self) -> dict:
        return asdict(self)

    def normalized(self) -> "Prediction":
        total = self.home_win + self.draw + self.away_win
        if total <= 0:
            return Prediction(1 / 3, 1 / 3, 1 / 3, self.source, self.rationale)
        return Prediction(
            self.home_win / total,
            self.draw / total,
            self.away_win / total,
            self.source,
            self.rationale,
            self.baseline,
        )
