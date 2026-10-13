"""Tests for /api/live/* with the NBA CDN mocked out (no network)."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import live


def _team(tricode, name, score, periods, wins=1, losses=0):
    return {
        "teamId": 1,
        "teamName": name,
        "teamCity": name,
        "teamTricode": tricode,
        "wins": wins,
        "losses": losses,
        "score": score,
        "timeoutsRemaining": 3,
        "periods": [{"period": i + 1, "score": s} for i, s in enumerate(periods)],
    }


SCOREBOARD = {
    "scoreboard": {
        "gameDate": "2026-10-13",
        "games": [
            {
                "gameId": "0012600045",
                "gameCode": "20261013/CLEORL",
                "gameStatus": 2,
                "gameStatusText": "Q3 5:46",
                "period": 3,
                "gameClock": "PT05M46.00S",
                "gameTimeUTC": "2026-10-13T23:00:00Z",
                "gameLabel": "Preseason",
                "homeTeam": _team("ORL", "Magic", 87, [28, 22, 37]),
                "awayTeam": _team("CLE", "Cavaliers", 82, [24, 26, 32]),
                "gameLeaders": {
                    "homeLeaders": {"personId": 7, "name": "Paolo Banchero", "points": 24, "rebounds": 6, "assists": 3},
                    "awayLeaders": {"personId": 0, "name": ""},
                },
            },
            {
                "gameId": "0012600048",
                "gameCode": "20261013/GSWLAL",
                "gameStatus": 1,
                "gameStatusText": "10:00 pm ET",
                "period": 0,
                "gameClock": "",
                "gameTimeUTC": "2026-10-14T02:00:00Z",
                "homeTeam": _team("LAL", "Lakers", 0, [0, 0, 0, 0]),
                "awayTeam": _team("GSW", "Warriors", 0, [0, 0, 0, 0]),
            },
        ],
    }
}

SCHEDULE = {
    "leagueSchedule": {
        "gameDates": [
            {
                "gameDate": "10/12/2026 00:00:00",
                "games": [
                    {
                        "gameId": "0012600043",
                        "gameCode": "20261012/MINNYK",
                        "gameStatus": 3,
                        "gameStatusText": "Final",
                        "gameDateTimeUTC": "2026-10-12T23:30:00Z",
                        "homeTeam": _team("NYK", "Knicks", 104, []),
                        "awayTeam": _team("MIN", "Timberwolves", 122, []),
                        "pointsLeaders": [{"personId": 9, "firstName": "Anthony", "lastName": "Edwards", "teamTricode": "MIN", "points": 31.0}],
                    }
                ],
            },
            {
                "gameDate": "10/13/2026 00:00:00",
                "games": [
                    {
                        "gameId": "0012600045",
                        "gameCode": "20261013/CLEORL",
                        "gameStatus": 1,
                        "gameStatusText": "7:00 pm ET",
                        "homeTeam": _team("ORL", "Magic", 0, []),
                        "awayTeam": _team("CLE", "Cavaliers", 0, []),
                    }
                ],
            },
            {
                "gameDate": "10/14/2026 00:00:00",
                "games": [
                    {
                        "gameId": "0012600017",
                        "gameCode": "20261014/CHABOS",
                        "gameStatus": 1,
                        "gameStatusText": "7:30 pm ET",
                        "gameDateTimeUTC": "2026-10-14T23:30:00Z",
                        "homeTeam": _team("BOS", "Celtics", 0, []),
                        "awayTeam": _team("CHA", "Hornets", 0, []),
                    }
                ],
            },
        ]
    }
}


def _player(pid, name, pts, reb, ast, played="1"):
    first, _, last = name.partition(" ")
    return {
        "personId": pid,
        "name": name,
        "nameI": f"{first[0]}. {last}",
        "firstName": first,
        "familyName": last,
        "starter": "1",
        "oncourt": "0",
        "played": played,
        "statistics": {
            "minutes": "PT31M30.00S",
            "points": pts,
            "reboundsTotal": reb,
            "assists": ast,
            "fieldGoalsMade": 10,
            "fieldGoalsAttempted": 18,
            "plusMinusPoints": 12.0,
        },
    }


BOX_0043 = {
    "game": {
        "gameId": "0012600043",
        "gameCode": "20261012/MINNYK",
        "gameStatus": 3,
        "gameStatusText": "Final",
        "period": 4,
        "gameClock": "PT00M00.00S",
        "homeTeam": {
            **_team("NYK", "Knicks", 104, [20, 30, 24, 30]),
            "statistics": {"fieldGoalsMade": 40, "reboundsTotal": 41},
            "players": [_player(1, "Jalen Brunson", 22, 3, 7), _player(2, "Karl-Anthony Towns", 18, 12, 2)],
        },
        "awayTeam": {
            **_team("MIN", "Timberwolves", 122, [30, 30, 30, 32]),
            "statistics": {"fieldGoalsMade": 45, "reboundsTotal": 47},
            "players": [_player(9, "Anthony Edwards", 31, 5, 4), _player(10, "Nikola Jokić", 0, 0, 0, played="0")],
        },
    }
}


@pytest.fixture()
def client(monkeypatch):
    live.clear_cache()
    calls: list[str] = []

    def fake_get(path):
        calls.append(path)
        if path == live.SCOREBOARD_PATH:
            return SCOREBOARD
        if path == live.SCHEDULE_PATH:
            return SCHEDULE
        if path.endswith("boxscore_0012600043.json"):
            return BOX_0043
        raise live.LiveFetchError(f"{path}: HTTP 403")

    monkeypatch.setattr(live, "_http_get_json", fake_get)
    app = FastAPI()
    app.include_router(live.router)
    c = TestClient(app)
    c.calls = calls  # type: ignore[attr-defined]
    yield c
    live.clear_cache()


def test_format_clock_and_period_labels():
    assert live.format_clock("PT05M46.00S") == "5:46"
    assert live.format_clock("PT00M34.50S") == "34.5"
    assert live.format_clock("") == ""
    assert live.period_label(2) == "Q2"
    assert live.period_label(5) == "OT"
    assert live.period_label(6) == "2OT"


def test_scoreboard_normalizes_and_sorts_live_first(client):
    body = client.get("/api/live/scoreboard").json()
    assert body["success"] is True
    data = body["data"]
    assert data["date"] == "2026-10-13"
    assert data["hasLive"] is True
    first = data["games"][0]
    assert first["gameId"] == "0012600045"
    assert first["state"] == "live"
    assert first["periodText"] == "Q3"
    assert first["clock"] == "5:46"
    assert first["home"]["tricode"] == "ORL"
    assert first["home"]["periods"] == [28, 22, 37]
    assert first["leaders"]["home"]["name"] == "Paolo Banchero"
    assert first["leaders"]["away"] is None
    assert data["games"][1]["state"] == "scheduled"


def test_scoreboard_is_cached(client):
    client.get("/api/live/scoreboard")
    client.get("/api/live/scoreboard")
    assert client.calls.count(live.SCOREBOARD_PATH) == 1


def test_game_box_score_and_leaders(client):
    body = client.get("/api/live/game/0012600043").json()
    assert body["success"] is True
    data = body["data"]
    assert data["game"]["state"] == "final"
    assert data["game"]["periodText"] == "Final"
    assert data["teams"]["away"]["tricode"] == "MIN"
    assert data["teams"]["home"]["statistics"]["reb"] == 41
    assert data["leaders"]["points"][0]["name"] == "Anthony Edwards"
    # DNP players are excluded from leaders
    assert all(p["name"] != "Nikola Jokić" for p in data["leaders"]["points"])
    assert data["teams"]["home"]["players"][0]["minutes"] == 31.5


def test_game_missing_box_is_graceful(client):
    body = client.get("/api/live/game/0012600099").json()
    assert body["success"] is False
    assert body["data"] is None
    assert "not available" in body["meta"]["message"]


def test_game_rejects_bad_id(client):
    body = client.get("/api/live/game/abc").json()
    assert body["success"] is False


def test_schedule_past_day_and_today_overlay(client):
    past = client.get("/api/live/schedule", params={"date": "2026-10-12"}).json()
    assert past["success"] is True
    g = past["data"]["games"][0]
    assert g["state"] == "final"
    assert g["away"]["score"] == 122
    assert g["pointsLeader"]["name"] == "Anthony Edwards"
    assert past["data"]["nextDate"] == "2026-10-13"

    today = client.get("/api/live/schedule", params={"date": "2026-10-13"}).json()
    # live scoreboard state wins over the static schedule's "scheduled"
    assert today["data"]["games"][0]["state"] == "live"


def test_schedule_bad_date(client):
    body = client.get("/api/live/schedule", params={"date": "13-10-2026"}).json()
    assert body["success"] is False
    assert body["data"]["games"] == []


def test_board_with_players(client):
    body = client.get(
        "/api/live/board",
        params={"past_days": 2, "players": "Anthony Edwards,Nikola Jokic:DEN,Jayson Tatum:BOS"},
    ).json()
    assert body["success"] is True
    data = body["data"]
    assert data["today"]["hasLive"] is True
    assert [d["date"] for d in data["pastDays"]] == ["2026-10-12"]
    assert data["upcoming"]["date"] == "2026-10-14"
    by_name = {p["query"]: p for p in data["players"]}
    ant = by_name["Anthony Edwards"]
    assert ant["found"] and ant["line"]["pts"] == 31 and ant["line"]["opponentTricode"] == "NYK"
    # accent-insensitive match
    assert by_name["Nikola Jokic"]["found"] is True
    tatum = by_name["Jayson Tatum"]
    assert tatum["found"] is False
    assert tatum["playsToday"] is False
    assert tatum["nextGame"]["gameId"] == "0012600017"
    assert tatum["nextGame"]["opponent"] == "CHA"


def test_everything_down_returns_empty_not_500(monkeypatch):
    live.clear_cache()

    def boom(path):
        raise live.LiveFetchError("HTTP 403")

    monkeypatch.setattr(live, "_http_get_json", boom)
    app = FastAPI()
    app.include_router(live.router)
    c = TestClient(app)
    for url in ("/api/live/scoreboard", "/api/live/board", "/api/live/schedule?date=2026-10-12"):
        r = c.get(url)
        assert r.status_code == 200
        assert r.json()["success"] is False
    live.clear_cache()


def test_stale_cache_served_when_upstream_fails(monkeypatch):
    live.clear_cache()
    monkeypatch.setattr(live, "_http_get_json", lambda p: SCOREBOARD)
    live.get_scoreboard()
    # expire it, then break upstream
    for k, (exp, val) in list(live._cache.items()):
        live._cache[k] = (0.0, val)

    def boom(path):
        raise live.LiveFetchError("down")

    monkeypatch.setattr(live, "_http_get_json", boom)
    value, from_cache = live.get_scoreboard()
    assert from_cache is True
    assert value["date"] == "2026-10-13"
    live.clear_cache()
