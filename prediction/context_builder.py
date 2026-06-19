"""Assemble the prediction context bundle from seed profiles + live state.

For v1 the team profiles are loaded from the static JSON files produced by the
research orchestrator (``prediction/data/profiles/<iso3>.json``). The live
pipeline (see ``prediction/pipeline/sources.py``) can later overlay fresh
rankings and the live match clock on top of these.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .schema import MatchState, TeamProfile, PredictionContext

PROFILES_DIR = Path(__file__).parent / "data" / "profiles"


def load_profile(iso3: str, profiles_dir: Optional[Path] = None) -> TeamProfile:
    """Load a single team profile by ISO3 code (case-insensitive)."""
    base = profiles_dir or PROFILES_DIR
    path = base / f"{iso3.lower()}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No profile for '{iso3}' at {path}. "
            "Has the research orchestrator produced seed data yet?"
        )
    with path.open() as fh:
        return TeamProfile.from_dict(json.load(fh))


def build_context(
    home_iso3: str,
    away_iso3: str,
    match_state: Optional[MatchState] = None,
    profiles_dir: Optional[Path] = None,
) -> PredictionContext:
    """Build the full context bundle for a fixture.

    ``match_state`` defaults to a pre-match clock when omitted.
    """
    return PredictionContext(
        home=load_profile(home_iso3, profiles_dir),
        away=load_profile(away_iso3, profiles_dir),
        match_state=match_state or MatchState(),
    )
