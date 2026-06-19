# Soccer Prediction (World Cup 2026)

Hybrid match-outcome predictor. Full scope: [`docs/soccer_prediction_scope.md`](../docs/soccer_prediction_scope.md).

```
context bundle = ranking gap + team profiles + media sentiment + live match clock
        │
        ├── deterministic.py   in-play Poisson baseline (pure, reproducible)
        └── llm_adjuster.py     claude-opus-4-8 nudges within ±0.15, never overrides
```

## Quick start

```python
from prediction import build_context, baseline_prediction
from prediction.schema import MatchState, Phase
from prediction.llm_adjuster import adjust_prediction

# Pre-match, using seed profiles in prediction/data/profiles/
ctx = build_context("ARG", "FRA")
print(baseline_prediction(ctx).as_dict())

# Live: 1-0 with 88' on the clock — the model trusts the lead.
ctx.match_state = MatchState(phase=Phase.SECOND_HALF, minute=88,
                             home_score=1, away_score=0)
print(baseline_prediction(ctx).as_dict())

# Hybrid (inject your LLM transport as a callable; falls back to baseline if omitted)
print(adjust_prediction(ctx, llm_call=my_llm).as_dict())
```

## Pieces
| File | Role |
|------|------|
| `schema.py` | Context-bundle data contracts + match-clock math (regulation/added/extra time). |
| `deterministic.py` | Baseline probabilities from ranking gap + scoreline + minutes remaining. |
| `llm_adjuster.py` | Bounded LLM adjustment over player/media narrative context. |
| `context_builder.py` | Loads seed team profiles and assembles the bundle. |
| `pipeline/sources.py` | Adapter interfaces for live rankings / match clock / lineups. |
| `data/profiles/` | Seed team profiles (produced by the research orchestrator). |

Tests: `python tests/test_prediction.py`
