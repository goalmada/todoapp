"""Smoke tests for the deterministic in-play model and the hybrid adjuster.

These build profiles in-memory so they don't depend on the research seed data.
Run with: ``python -m pytest tests/test_prediction.py``  (or just execute the
file directly).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prediction.schema import (  # noqa: E402
    MatchState, Phase, TeamProfile, PredictionContext, Prediction,
)
from prediction.deterministic import baseline_prediction  # noqa: E402
from prediction.llm_adjuster import adjust_prediction, MAX_ADJUSTMENT  # noqa: E402


def _ctx(home_rank, away_rank, state):
    home = TeamProfile(team="Home", iso3="HOM", fifa_rank=home_rank,
                       fifa_points=2000 - home_rank * 10)
    away = TeamProfile(team="Away", iso3="AWY", fifa_rank=away_rank,
                       fifa_points=2000 - away_rank * 10)
    return PredictionContext(home=home, away=away, match_state=state)


def _assert_normalized(p: Prediction):
    total = p.home_win + p.draw + p.away_win
    assert abs(total - 1.0) < 1e-9, f"probabilities sum to {total}"


def test_favourite_leads_pre_match():
    p = baseline_prediction(_ctx(1, 40, MatchState(phase=Phase.PRE_MATCH)))
    _assert_normalized(p)
    assert p.home_win > p.away_win, "better-ranked side should be favoured"


def test_clock_locks_in_a_late_lead():
    """A 1-0 lead is worth far more with 5' left than at kick-off."""
    early = baseline_prediction(_ctx(20, 18, MatchState(
        phase=Phase.SECOND_HALF, minute=50, home_score=1, away_score=0)))
    late = baseline_prediction(_ctx(20, 18, MatchState(
        phase=Phase.SECOND_HALF, minute=88, home_score=1, away_score=0)))
    _assert_normalized(early)
    _assert_normalized(late)
    assert late.home_win > early.home_win, "less time left => lead more secure"
    assert late.draw < early.draw


def test_added_time_extends_the_clock():
    """5 minutes of announced added time keeps the comeback alive a bit longer."""
    no_added = baseline_prediction(_ctx(20, 18, MatchState(
        phase=Phase.SECOND_HALF, minute=90, home_score=0, away_score=1)))
    with_added = baseline_prediction(_ctx(20, 18, MatchState(
        phase=Phase.SECOND_HALF, minute=90, added_time=5,
        home_score=0, away_score=1)))
    assert with_added.draw > no_added.draw, "added time => more chance to equalise"


def test_knockout_has_no_draw():
    """A level knockout tie resolves via the shootout model, never a draw."""
    p = baseline_prediction(_ctx(10, 12, MatchState(
        phase=Phase.SECOND_HALF, minute=80, home_score=1, away_score=1,
        is_knockout=True)))
    _assert_normalized(p)
    assert p.draw == 0.0
    assert p.home_win > 0 and p.away_win > 0


def test_extra_time_clock():
    """During extra time, the regulation clock is spent but ET minutes remain."""
    state = MatchState(phase=Phase.EXTRA_FIRST, minute=100,
                       home_score=0, away_score=0, is_knockout=True)
    assert state.regulation_minutes_remaining == 0.0
    assert state.extra_time_minutes_remaining == 20.0
    p = baseline_prediction(_ctx(5, 6, state))
    _assert_normalized(p)
    assert p.draw == 0.0  # knockout


def test_finished_match_is_certain():
    p = baseline_prediction(_ctx(30, 2, MatchState(
        phase=Phase.FULL_TIME, home_score=2, away_score=1)))
    assert p.home_win == 1.0


def test_hybrid_falls_back_without_llm():
    ctx = _ctx(1, 40, MatchState(phase=Phase.PRE_MATCH))
    base = baseline_prediction(ctx)
    hybrid = adjust_prediction(ctx)  # no llm_call provided
    assert (hybrid.home_win, hybrid.draw, hybrid.away_win) == (
        base.home_win, base.draw, base.away_win)


def test_hybrid_adjustment_is_bounded():
    ctx = _ctx(20, 22, MatchState(phase=Phase.PRE_MATCH))
    base = baseline_prediction(ctx)

    # A rogue LLM trying to force a near-certain home win.
    def rogue_llm(_prompt):
        return '{"home_win": 0.99, "draw": 0.005, "away_win": 0.005, "rationale": "x"}'

    hybrid = adjust_prediction(ctx, llm_call=rogue_llm)
    _assert_normalized(hybrid)
    # The move is clipped to MAX_ADJUSTMENT per outcome before renormalizing, so
    # the rogue's demanded near-certainty (0.99) is reined in: it may nudge, not
    # override. It still moves in the requested direction, but stays well short.
    assert hybrid.home_win > base.home_win, "should nudge toward the LLM's view"
    assert hybrid.home_win < 0.75, "must not be talked into near-certainty"
    assert hybrid.source == "hybrid"
    assert hybrid.baseline is not None


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nAll {len(fns)} tests passed.")
