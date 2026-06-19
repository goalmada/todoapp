"""Deterministic in-play baseline model.

Pure and reproducible: no network, no randomness. It combines three signals
from the context bundle:

1. **Ranking gap** (the global ranking table) -> a pre-match expected-goals
   supremacy between the two teams.
2. **Current scoreline** -> the goals already banked.
3. **Match clock** -> how many goals are still realistically scoreable. As the
   remaining minutes shrink, the pre-match prior matters less and the current
   scoreline dominates, because there is simply less football left to change it.

The remaining goals are modelled as independent Poisson variables whose rate is
the full-match expectation scaled by the fraction of the match still to play
(regulation + extra time). Outcome probabilities are obtained by enumerating the
joint distribution of additional goals on top of the current score.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from .schema import MatchState, Phase, Prediction, PredictionContext

# Average total goals in a men's World Cup match, used as the scoring budget.
BASE_TOTAL_GOALS = 2.6
# Per-team floor so a heavy favourite never drops a side to literally zero rate.
MIN_TEAM_LAMBDA = 0.15
# How many additional goals (per team) to enumerate; the Poisson tail beyond
# this is negligible for the rates involved.
MAX_EXTRA_GOALS = 10


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _full_match_supremacy(ctx: PredictionContext) -> float:
    """Expected home-minus-away goal supremacy over a full match.

    Prefers FIFA ranking points, then ranking position, then the researched
    ``strength_index``. Returns 0.0 (even match) when nothing is known so the
    model degrades gracefully to a neutral prior.
    """
    points_gap = ctx.points_gap()
    if points_gap is not None:
        # ~150 FIFA points of separation ≈ one goal of expected supremacy.
        return _clamp(points_gap / 150.0, -2.5, 2.5)

    rank_gap = ctx.rank_gap()
    if rank_gap is not None:
        # Positive rank_gap => home better ranked => positive supremacy.
        return _clamp(rank_gap * 0.03, -2.5, 2.5)

    sh, sa = ctx.home.strength_index, ctx.away.strength_index
    if sh is not None and sa is not None:
        return _clamp((sh - sa) / 20.0, -2.5, 2.5)

    return 0.0


def _full_match_lambdas(ctx: PredictionContext) -> Tuple[float, float]:
    """Full-match expected goals for (home, away)."""
    sup = _full_match_supremacy(ctx)
    home = max(MIN_TEAM_LAMBDA, (BASE_TOTAL_GOALS + sup) / 2.0)
    away = max(MIN_TEAM_LAMBDA, (BASE_TOTAL_GOALS - sup) / 2.0)
    return home, away


def _remaining_fraction(state: MatchState) -> float:
    """Fraction of a full 90' match's scoring opportunity still to come.

    Extra time adds another 30' of opportunity on top of any regulation time
    left. Capped so a long stoppage-time clock never exceeds a full match.
    """
    if state.phase == Phase.PRE_MATCH:
        return 1.0
    if state.is_finished:
        return 0.0
    remaining = state.regulation_minutes_remaining + state.extra_time_minutes_remaining
    return _clamp(remaining / 90.0, 0.0, 1.0)


def _outcome_from_goal_dists(
    home_now: int, away_now: int, lam_home: float, lam_away: float
) -> Tuple[float, float, float]:
    """Enumerate additional goals to get P(home win / draw / away win)."""
    p_home = p_draw = p_away = 0.0
    for i in range(MAX_EXTRA_GOALS + 1):
        pi = _poisson_pmf(i, lam_home)
        for j in range(MAX_EXTRA_GOALS + 1):
            pj = _poisson_pmf(j, lam_away)
            prob = pi * pj
            final_home, final_away = home_now + i, away_now + j
            if final_home > final_away:
                p_home += prob
            elif final_home == final_away:
                p_draw += prob
            else:
                p_away += prob
    return p_home, p_draw, p_away


def _resolve_knockout_draw(
    p_draw: float, ctx: PredictionContext
) -> Tuple[float, float]:
    """Split residual draw mass into (home, away) for a knockout tie.

    A level knockout score is not terminal: it goes to a penalty shootout.
    Shootouts are close to a coin flip, nudged slightly by relative strength.
    """
    sup = _full_match_supremacy(ctx)
    home_edge = _clamp(0.5 + sup * 0.05, 0.35, 0.65)
    return p_draw * home_edge, p_draw * (1.0 - home_edge)


def baseline_prediction(ctx: PredictionContext) -> Prediction:
    """Compute the deterministic baseline probabilities for the context."""
    state = ctx.match_state

    # Terminal state: the result is already (almost) decided.
    if state.is_finished:
        if state.home_score > state.away_score:
            return Prediction(1.0, 0.0, 0.0, source="deterministic",
                              rationale="Match finished; home won.")
        if state.home_score < state.away_score:
            return Prediction(0.0, 0.0, 1.0, source="deterministic",
                              rationale="Match finished; away won.")
        return Prediction(0.0, 1.0, 0.0, source="deterministic",
                          rationale="Match finished level.")

    full_home, full_away = _full_match_lambdas(ctx)
    frac = _remaining_fraction(state)
    lam_home, lam_away = full_home * frac, full_away * frac

    p_home, p_draw, p_away = _outcome_from_goal_dists(
        state.home_score, state.away_score, lam_home, lam_away
    )

    # In a knockout a draw can't stand: redistribute it via the shootout model.
    if state.is_knockout:
        add_home, add_away = _resolve_knockout_draw(p_draw, ctx)
        p_home, p_away, p_draw = p_home + add_home, p_away + add_away, 0.0

    rationale = (
        f"Ranking supremacy {_full_match_supremacy(ctx):+.2f} goals; "
        f"{frac * 90:.0f} min of scoring opportunity remaining; "
        f"score {state.home_score}-{state.away_score}."
    )
    return Prediction(p_home, p_draw, p_away, source="deterministic",
                      rationale=rationale).normalized()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
