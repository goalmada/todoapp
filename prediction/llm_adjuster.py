"""LLM adjustment layer of the hybrid engine.

The deterministic model produces a numeric baseline from the ranking gap, the
scoreline and the clock. This layer hands that baseline to an LLM together with
the *narrative* context the numbers can't see — key players, playing style and
media/historical sentiment — and lets the model nudge the probabilities.

Design rules:
- The LLM may only **adjust**, never override: the per-outcome change is bounded
  by ``MAX_ADJUSTMENT`` so a strong baseline (e.g. a 3-0 lead with 5 minutes
  left) cannot be talked into nonsense.
- The output always carries the baseline alongside the final probabilities so
  every adjustment is auditable.
- The model id is ``claude-opus-4-8``.
"""

from __future__ import annotations

import json
from typing import Optional

from .schema import Prediction, PredictionContext
from .deterministic import baseline_prediction

MODEL_ID = "claude-opus-4-8"
# Maximum the LLM may move any single outcome's probability, in absolute terms.
MAX_ADJUSTMENT = 0.15


def _profile_brief(profile) -> dict:
    """Compact, LLM-friendly view of a team profile."""
    return {
        "team": profile.team,
        "fifa_rank": profile.fifa_rank,
        "style": profile.style,
        "recent_form": profile.recent_form,
        "key_players": [
            {"name": p.name, "position": p.position, "role": p.role, "note": p.note}
            for p in profile.key_players
        ],
        "historical_news": profile.historical_news,
        "media_sentiment": {
            "label": profile.media_sentiment.label,
            "confidence": profile.media_sentiment.confidence,
            "summary": profile.media_sentiment.summary,
        },
    }


def build_prompt(ctx: PredictionContext, baseline: Prediction) -> str:
    """Render the context bundle + baseline into the adjuster prompt."""
    state = ctx.match_state
    payload = {
        "baseline_probabilities": {
            "home_win": round(baseline.home_win, 4),
            "draw": round(baseline.draw, 4),
            "away_win": round(baseline.away_win, 4),
        },
        "match_state": {
            "phase": state.phase.value,
            "minute": state.minute,
            "added_time": state.added_time,
            "regulation_minutes_remaining": state.regulation_minutes_remaining,
            "extra_time_minutes_remaining": state.extra_time_minutes_remaining,
            "is_knockout": state.is_knockout,
            "score": f"{state.home_score}-{state.away_score}",
        },
        "home": _profile_brief(ctx.home),
        "away": _profile_brief(ctx.away),
    }
    return (
        "You are adjusting a World Cup 2026 match prediction.\n"
        "A deterministic model already produced baseline probabilities from the\n"
        "FIFA ranking gap, the current scoreline and the match clock. Using the\n"
        "team profiles, key players and media/historical sentiment below, you may\n"
        f"nudge each probability by at most {MAX_ADJUSTMENT:.2f} in absolute terms.\n"
        "Respect the clock: with little time left, trust the baseline more.\n\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n\n"
        "Respond with ONLY a JSON object:\n"
        '{"home_win": <float>, "draw": <float>, "away_win": <float>, '
        '"rationale": "<one or two sentences>"}\n'
        "The three probabilities must sum to 1.0."
    )


def _bound_and_normalize(baseline: Prediction, raw: dict, rationale: str) -> Prediction:
    """Clip the LLM's move to MAX_ADJUSTMENT per outcome, then renormalize."""
    def clip(name: str, base: float) -> float:
        proposed = float(raw.get(name, base))
        lo, hi = base - MAX_ADJUSTMENT, base + MAX_ADJUSTMENT
        return max(0.0, min(1.0, max(lo, min(hi, proposed))))

    adjusted = Prediction(
        home_win=clip("home_win", baseline.home_win),
        draw=clip("draw", baseline.draw),
        away_win=clip("away_win", baseline.away_win),
        source="hybrid",
        rationale=rationale,
        baseline=baseline,
    )
    return adjusted.normalized()


def adjust_prediction(
    ctx: PredictionContext,
    baseline: Optional[Prediction] = None,
    llm_call=None,
) -> Prediction:
    """Run the hybrid prediction.

    ``llm_call`` is an injectable callable ``(prompt: str) -> str`` returning the
    model's JSON text. It is injected (rather than hard-wired to an SDK) so the
    engine stays testable and the transport — Anthropic SDK, an internal gateway,
    etc. — can be chosen at the call site. When omitted, the deterministic
    baseline is returned unchanged so the system always degrades safely.
    """
    base = baseline or baseline_prediction(ctx)
    if llm_call is None:
        return base

    prompt = build_prompt(ctx, base)
    try:
        text = llm_call(prompt)
        raw = json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError):
        # Any malformed LLM output falls back to the trustworthy baseline.
        return base

    rationale = str(raw.get("rationale", "")) or base.rationale
    return _bound_and_normalize(base, raw, rationale)
