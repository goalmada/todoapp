# Seed Profile Coverage Report — World Cup 2026

_Generated from the research orchestrator ("Thor") and its parallel workers._

## Coverage
- **48 of 48** national-team profiles produced — full field (see `_index.json`).
- FIFA World Ranking basis: published **2026-06-11** (`as_of` in each profile).
- Every profile carries source URLs (2-4 each) backing its ranking, squad and
  sentiment claims; no fabricated data (no `data_quality` fallback flags needed).
- Each profile has `style`, `recent_form`, `strength_index`, key players,
  `historical_news`, and a `media_sentiment` synthesis.

## Teams covered (team and FIFA rank)
Argentina (1), Spain (2), France (3), England (4), Portugal (5), Brazil (6), Morocco (7), Netherlands (7), Belgium (9), Germany (10), Croatia (11), Colombia (13), Mexico (14), Senegal (15), Uruguay (16), USA (17), Japan (18), Switzerland (19), IR Iran (20), Türkiye (22), Ecuador (23), Austria (24), Korea Republic (25), Australia (27), Algeria (28), Egypt (29), Canada (30), Norway (31), Côte d'Ivoire (33), Panama (34), Sweden (38), Scotland (40), Czechia (41), Paraguay (42), Tunisia (45), Congo DR (46), Uzbekistan (50), Qatar (56), Iraq (57), South Africa (60), Saudi Arabia (61), Jordan (63), Bosnia and Herzegovina (64), Cabo Verde (67), Ghana (73), Curacao (82), Haiti (83), New Zealand (85).

## Known data issues / follow-ups
- **Shared rank 7**: Morocco and Netherlands both resolved to rank 7 due to conflicting
  sources (official vs in-tournament live ranking). The deterministic model treats
  this as an equal prior between them; re-confirm against the final official table.
- **`fifa_points` null** for several teams where the exact 2026-06-11 figure could
  not be sourced (April-2026 approximations existed but were not used, to avoid
  fabrication). The deterministic model falls back to ranking position in that case.
- Rankings are a snapshot — the live `RankingSource` adapter should refresh
  `fifa_rank`/`fifa_points` before each prediction.
- Notable squad/injury context (e.g. Japan without Mitoma/Endo, Canada's Davies
  hamstring, omissions like Kudus/Azmoun/Haller) is captured in each profile text.

## Validation
- All 48 files parse as well-formed JSON.
- Profiles validate against `prediction/schema.py::TeamProfile.from_dict` and load
  cleanly through `prediction/context_builder.py`.
