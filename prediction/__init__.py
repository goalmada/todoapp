"""Soccer prediction context system for the FIFA World Cup 2026.

Hybrid engine: a deterministic in-play baseline (ranking gap + scoreline +
match clock) adjusted by an LLM layer that reasons over team profiles and
media sentiment. See ``docs/soccer_prediction_scope.md`` for the full scope.
"""

from .schema import (
    Phase,
    KeyPlayer,
    MediaSentiment,
    TeamProfile,
    MatchState,
    PredictionContext,
    Prediction,
)
from .deterministic import baseline_prediction
from .context_builder import build_context
from .llm_adjuster import adjust_prediction
from .transport import make_anthropic_llm_call

__all__ = [
    "Phase",
    "KeyPlayer",
    "MediaSentiment",
    "TeamProfile",
    "MatchState",
    "PredictionContext",
    "Prediction",
    "baseline_prediction",
    "build_context",
    "adjust_prediction",
    "make_anthropic_llm_call",
]
