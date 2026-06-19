# Soccer Prediction Context System — Scope (World Cup 2026)

> Status: scope / spec. Owned by the orchestrator (**Thor**) and the core engine.
> Target competition: **FIFA World Cup 2026** (48 national teams).
> Prediction engine: **Hybrid** — deterministic in-play baseline + LLM adjustment layer.

## 1. Goal

Produce, for any World Cup 2026 match (pre-match or live), a probability
distribution over the three outcomes from the perspective of the match's
current state:

```
{ "home_win": p, "draw": p, "away_win": p }   # sums to 1.0
```

The prediction is driven by a **context bundle** assembled per match and
injected into the engine. The same bundle feeds both the deterministic model
(numeric fields) and the LLM adjuster (numeric + narrative fields).

## 2. The Context Bundle

This is the single object injected into the prediction engine. Every field has
a clear owner (who produces it) and a consumer (deterministic / LLM / both).

### 2.1 Ranking context  *(consumer: deterministic + LLM)*
For each of the two teams:
- `fifa_rank` — current position in the FIFA World Ranking (the "global ranking table").
- `fifa_points` — current FIFA ranking points.
- Derived: `rank_gap`, `points_gap` (home minus away).

The ranking gap is the **primary prior** in the deterministic model. It is the
explicit answer to "take into account the position of each team in the global
ranking table."

### 2.2 Team profile  *(owner: Thor research workers; consumer: LLM, partial deterministic)*
For each team a profile document (see §4 schema):
- `key_players` — main players, with position, role, and a short scouting note.
- `style` — playing style summary (e.g. high press, low block, possession).
- `recent_form` — last-N results / qualifying narrative.
- `strength_index` — optional 0–100 numeric the deterministic layer may blend in.

### 2.3 Media / historical sentiment  *(owner: Thor research workers; consumer: LLM)*
For each team and its key players:
- `historical_news` — notable historical storylines (triumphs, chokes, scandals, rivalries).
- `media_sentiment` — a short synthesis of "what the media thinks" right now,
  with a coarse polarity label (`positive` / `neutral` / `negative`) and confidence.

This is **narrative context** for the LLM only. It must never silently leak into
the deterministic numbers; if we want it numeric, it goes through `strength_index`.

### 2.4 Match state / clock  *(owner: live pipeline; consumer: deterministic + LLM)*
This is the time-awareness requirement. Fields:
- `phase` — `PRE_MATCH` | `FIRST_HALF` | `HALF_TIME` | `SECOND_HALF` |
  `EXTRA_FIRST` | `EXTRA_HALF_TIME` | `EXTRA_SECOND` | `PENALTIES` | `FULL_TIME`.
- `minute` — current match minute (clock).
- `added_time` — announced stoppage/added minutes for the current period (nullable).
- `regulation_minutes_remaining` — minutes left in 90' regulation (incl. added time).
- `extra_time_minutes_remaining` — minutes left in 30' extra time, if applicable.
- `is_knockout` — knockout matches can go to extra time + penalties; group games cannot.
- `home_score`, `away_score` — current scoreline.

The clock is **first-class**: as time remaining shrinks, the current scoreline
dominates the prediction and the pre-match ranking prior decays toward zero
influence. Extra time and the knockout/group distinction change how much football
is left to play and whether a draw is a terminal outcome.

## 3. Engine (Hybrid)

```
context bundle
      │
      ├─► deterministic baseline  ──►  P_base{home,draw,away}
      │     (ranking gap + scoreline + time remaining, in-play Poisson)
      │
      └─► LLM adjuster (claude-opus-4-8)
            input: P_base + team profiles + media sentiment + match state
            output: P_final{home,draw,away} + short rationale + adjustment delta
```

- **Deterministic baseline** (`prediction/deterministic.py`): pure, reproducible,
  no network. Pre-match prior from ranking gap (Elo-style expected goals), plus an
  in-play Poisson model for remaining goals scaled by minutes left (regulation +
  extra time). Group-stage draws are terminal; knockout draws roll into ET/penalties.
- **LLM adjuster** (`prediction/llm_adjuster.py`): receives the baseline and the
  narrative context, returns adjusted probabilities, a bounded adjustment (so the
  LLM can nudge, not override), and a rationale. Uses `claude-opus-4-8`.
- The hybrid output always carries both `baseline` and `final` so adjustments are auditable.

## 4. Data contract — team profile (seed JSON)

Thor's workers produce one file per team at
`prediction/data/profiles/<iso3>.json` (e.g. `arg.json`, `bra.json`):

```json
{
  "team": "Argentina",
  "iso3": "ARG",
  "fifa_rank": 1,
  "fifa_points": 1860.23,
  "as_of": "2026-06-01",
  "style": "Possession-based, compact mid-block, lethal on transitions.",
  "recent_form": "Reigning champions; strong qualifying campaign.",
  "strength_index": 95,
  "key_players": [
    {
      "name": "Lionel Messi",
      "position": "RW/CAM",
      "role": "Captain, creative talisman",
      "note": "Decisive in knockouts; set-piece and final-third threat."
    }
  ],
  "historical_news": [
    "2022 World Cup winners.",
    "Long-running GOAT narrative around Messi's final World Cup."
  ],
  "media_sentiment": {
    "label": "positive",
    "confidence": 0.8,
    "summary": "Media frame them as favourites carried by experience and Messi."
  },
  "sources": ["https://..."]
}
```

Field rules:
- All numeric fields nullable; the deterministic model degrades gracefully (falls
  back to neutral priors when `fifa_rank`/`strength_index` are missing).
- `sources` is required for any factual claim in `historical_news` / `media_sentiment`.

## 5. Data sourcing strategy

- **Seed (now):** Thor's workers research and write the static profile JSONs above.
  Rankings come from the latest published FIFA World Ranking; players/news/sentiment
  from reputable football media.
- **Live (pipeline):** `prediction/pipeline/sources.py` defines adapter interfaces
  (`RankingSource`, `MatchStateSource`, `LineupSource`) to be wired to the existing
  soccer APIs. At prediction time the pipeline refreshes ranking + live match clock +
  lineups, overlaying the static profiles. Adapters are stubbed with a documented
  interface; API credentials/endpoints to be filled in once provided.

## 6. Thor (orchestrator) deliverables

1. One profile JSON per qualified WC2026 team in `prediction/data/profiles/`.
2. A `prediction/data/profiles/_index.json` listing teams + file paths + ranks.
3. Every factual claim cited via `sources`.
4. A short `prediction/data/profiles/_report.md` noting coverage, gaps, and any
   teams not yet qualified/known at research time.

## 7. Out of scope (for now)
- Real money / betting integration.
- Player-level injury feeds (can be added to the live pipeline later).
- Live websocket streaming (pipeline is pull-based for v1).
