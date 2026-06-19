"""Tests for API-Football adapters and source protocols.

Unit tests use mocked API responses so they run without network/keys.
Run with: ``python -m pytest tests/test_sources.py -v``
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prediction.schema import Phase, GoalEvent, GroupStanding, MatchState
from prediction.pipeline.sources import (
    ApiFootballMatchStateSource,
    ApiFootballLineupSource,
    ApiFootballStandingsSource,
    _STATUS_TO_PHASE,
    _api_football_request,
    LivePipeline,
)


def _mock_fixture_response(status_short="1H", elapsed=35, home_goals=1, away_goals=0,
                           round_str="Group Stage - 1", extra=None):
    return {
        "response": [{
            "fixture": {
                "id": 1489369,
                "status": {"short": status_short, "elapsed": elapsed, "extra": extra},
            },
            "league": {"round": round_str},
            "goals": {"home": home_goals, "away": away_goals},
            "events": [],
        }],
        "errors": [],
    }


def _mock_events_response(goals=None):
    events = []
    for g in (goals or []):
        events.append({
            "time": {"elapsed": g["minute"]},
            "type": "Goal",
            "detail": g.get("detail", "Normal Goal"),
            "team": {"name": g["team"]},
            "player": {"name": g["player"]},
            "assist": {"name": g.get("assist", "")},
        })
    return {"response": events, "errors": []}


def _mock_lineups_response():
    return {
        "response": [
            {
                "team": {"id": 16, "name": "Mexico"},
                "formation": "4-1-4-1",
                "startXI": [
                    {"player": {"id": 1, "name": "R. Rangel"}},
                    {"player": {"id": 2, "name": "I. Reyes"}},
                    {"player": {"id": 3, "name": "C. Montes"}},
                ],
                "substitutes": [],
            },
            {
                "team": {"id": 1531, "name": "South Africa"},
                "formation": "5-3-2",
                "startXI": [
                    {"player": {"id": 10, "name": "R. Williams"}},
                    {"player": {"id": 11, "name": "K. Mudau"}},
                ],
                "substitutes": [],
            },
        ],
        "errors": [],
    }


def _mock_standings_response():
    return {
        "response": [{
            "league": {
                "standings": [
                    [
                        {
                            "rank": 1, "team": {"id": 16, "name": "Mexico"},
                            "points": 6, "goalsDiff": 3, "group": "Group A",
                            "form": "WW", "status": "same",
                            "all": {"played": 2, "win": 2, "draw": 0, "lose": 0,
                                    "goals": {"for": 3, "against": 0}},
                        },
                        {
                            "rank": 2, "team": {"id": 17, "name": "South Korea"},
                            "points": 3, "goalsDiff": 0, "group": "Group A",
                            "form": "LW", "status": "same",
                            "all": {"played": 2, "win": 1, "draw": 0, "lose": 1,
                                    "goals": {"for": 2, "against": 2}},
                        },
                    ],
                ],
            },
        }],
        "errors": [],
    }


# --- MatchStateSource tests ---

@patch("prediction.pipeline.sources._api_football_request")
def test_match_state_first_half(mock_req):
    mock_req.side_effect = [
        _mock_fixture_response(status_short="1H", elapsed=35, home_goals=1, away_goals=0),
        _mock_events_response([{"minute": 9, "team": "Mexico", "player": "J. Quinones"}]),
    ]
    src = ApiFootballMatchStateSource(api_key="test-key")
    state = src.get_match_state("1489369")

    assert state.phase == Phase.FIRST_HALF
    assert state.minute == 35
    assert state.home_score == 1
    assert state.away_score == 0
    assert not state.is_knockout
    assert len(state.goals) == 1
    assert state.goals[0].player == "J. Quinones"
    assert state.goals[0].minute == 9


@patch("prediction.pipeline.sources._api_football_request")
def test_match_state_knockout(mock_req):
    mock_req.side_effect = [
        _mock_fixture_response(status_short="2H", elapsed=70, home_goals=2, away_goals=1,
                               round_str="Round of 16"),
        _mock_events_response([]),
    ]
    src = ApiFootballMatchStateSource(api_key="test-key")
    state = src.get_match_state("999")

    assert state.phase == Phase.SECOND_HALF
    assert state.is_knockout


@patch("prediction.pipeline.sources._api_football_request")
def test_match_state_full_time(mock_req):
    mock_req.side_effect = [
        _mock_fixture_response(status_short="FT", elapsed=90, home_goals=2, away_goals=0),
        _mock_events_response([
            {"minute": 9, "team": "Mexico", "player": "J. Quinones"},
            {"minute": 67, "team": "Mexico", "player": "R. Jimenez"},
        ]),
    ]
    src = ApiFootballMatchStateSource(api_key="test-key")
    state = src.get_match_state("1489369")

    assert state.phase == Phase.FULL_TIME
    assert state.is_finished
    assert len(state.goals) == 2


@patch("prediction.pipeline.sources._get_api_football_key", return_value=None)
@patch("prediction.pipeline.sources._api_football_request")
def test_match_state_no_key(mock_req, mock_key):
    src = ApiFootballMatchStateSource(api_key="")
    state = src.get_match_state("1489369")
    assert state.phase == Phase.PRE_MATCH
    mock_req.assert_not_called()


# --- LineupSource tests ---

@patch("prediction.pipeline.sources._api_football_request")
def test_lineup_returns_starters(mock_req):
    mock_req.return_value = _mock_lineups_response()
    src = ApiFootballLineupSource(api_key="test-key")
    starters = src.get_starters("1489369", "mexico")
    assert len(starters) == 3
    assert "R. Rangel" in starters


@patch("prediction.pipeline.sources._get_api_football_key", return_value=None)
@patch("prediction.pipeline.sources._api_football_request")
def test_lineup_no_key(mock_req, mock_key):
    src = ApiFootballLineupSource(api_key="")
    starters = src.get_starters("1489369", "MEX")
    assert starters == []
    mock_req.assert_not_called()


# --- StandingsSource tests ---

@patch("prediction.pipeline.sources._api_football_request")
def test_standings_group(mock_req):
    mock_req.return_value = _mock_standings_response()
    src = ApiFootballStandingsSource(api_key="test-key")
    standings = src.get_group_standings()

    assert len(standings) == 2
    mexico = standings[0]
    assert isinstance(mexico, GroupStanding)
    assert mexico.team == "Mexico"
    assert mexico.points == 6
    assert mexico.won == 2
    assert mexico.goal_diff == 3
    assert mexico.group == "Group A"


@patch("prediction.pipeline.sources._api_football_request")
def test_standings_team_lookup(mock_req):
    mock_req.return_value = _mock_standings_response()
    src = ApiFootballStandingsSource(api_key="test-key")
    korea = src.get_team_standing("South Korea")
    assert korea is not None
    assert korea.points == 3


@patch("prediction.pipeline.sources._api_football_request")
def test_standings_cache(mock_req):
    mock_req.return_value = _mock_standings_response()
    src = ApiFootballStandingsSource(api_key="test-key")
    src.get_group_standings()
    src.get_group_standings()
    assert mock_req.call_count == 1


# --- Status mapping coverage ---

def test_all_api_statuses_map_to_phase():
    known_statuses = [
        "TBD", "NS", "1H", "HT", "2H", "ET", "BT", "P",
        "FT", "AET", "PEN", "SUSP", "INT", "PST", "CANC",
        "ABD", "AWD", "WO", "LIVE",
    ]
    for s in known_statuses:
        assert s in _STATUS_TO_PHASE, f"Missing status mapping: {s}"
        assert isinstance(_STATUS_TO_PHASE[s], Phase)


# --- LivePipeline factory ---

def test_from_api_football_factory():
    pipeline = LivePipeline.from_api_football(api_key="test-key")
    assert pipeline.match_state_source is not None
    assert pipeline.lineup_source is not None
    assert pipeline.standings_source is not None
    assert isinstance(pipeline.match_state_source, ApiFootballMatchStateSource)


# --- GoalEvent dataclass ---

def test_goal_event_creation():
    g = GoalEvent(minute=45, team="Brazil", player="Neymar", detail="Penalty")
    assert g.minute == 45
    assert g.detail == "Penalty"
    assert g.assist == ""


def test_match_state_with_goals():
    goals = [
        GoalEvent(minute=10, team="A", player="P1"),
        GoalEvent(minute=55, team="B", player="P2"),
    ]
    state = MatchState(phase=Phase.SECOND_HALF, minute=60,
                       home_score=1, away_score=1, goals=goals)
    assert len(state.goals) == 2
    assert state.goals[0].minute == 10


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nAll {len(fns)} tests passed.")
