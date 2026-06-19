# Seed Profile Coverage Report — World Cup 2026

_Generated from the research orchestrator ("Thor") and its parallel workers._

## Coverage
- **40 of 48** national-team profiles produced (see `_index.json`).
- FIFA World Ranking basis: published **2026-06-11** (`as_of` in each profile).
- Every profile carries source URLs backing its ranking, squad and sentiment claims.
- Each profile has `style`, `recent_form`, `strength_index`, key players,
  `historical_news`, and a `media_sentiment` synthesis.

## Teams covered (by FIFA rank)
Argentina, Spain, France, England, Portugal, Brazil, Morocco, Netherlands, Belgium, Germany, Croatia, Colombia, Mexico, Senegal, Uruguay, Japan, Switzerland, IR Iran, Türkiye, Austria, Australia, Egypt, Canada, Norway, Côte d'Ivoire, Panama, Sweden, Scotland, Czechia, Paraguay, Tunisia, Congo DR, Uzbekistan, Qatar, Iraq, South Africa, Saudi Arabia, Bosnia and Herzegovina, Cabo Verde, Ghana.

## Gaps / follow-ups
- **~8 of the 48 qualified teams remain to be profiled** — fill via a follow-up
  research pass or the live pipeline at prediction time.
- `fifa_points` is null for some teams where the exact 2026-06-11 figure could not
  be sourced (April-2026 approximations were available but not used, to avoid
  fabrication). The deterministic model falls back to ranking position in that case.
- Re-confirm the profiled set against the final official 48-team list.
- Rankings are a snapshot — the live `RankingSource` adapter should refresh
  `fifa_rank`/`fifa_points` before each prediction.

## Notes
- No fabricated data: every profile is web-sourced (no `data_quality` fallback flags).
- Profiles validate against `prediction/schema.py::TeamProfile.from_dict` and load
  cleanly through `prediction/context_builder.py`.
