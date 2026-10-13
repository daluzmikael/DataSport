"""Live NBA scoreboard / box score / schedule endpoints for the home-prototype live board.

Source: NBA's public liveData + staticData JSON feeds (the same files nba_api's
``nba_api.live.nba.endpoints`` module reads). No API key is needed.

    {base}/liveData/scoreboard/todaysScoreboard_00.json
    {base}/liveData/boxscore/boxscore_{game_id}.json
    {base}/staticData/scheduleLeagueV2_1.json        (full season, ~5 MB)

``base`` is tried in order from ``NBA_LIVE_BASE_URLS`` (comma separated). Default:

    https://cdn.nba.com/static/json                                (Akamai; 403s some IPs)
    https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA (origin mirror, same files)

nba_api's live module hardcodes the cdn.nba.com base, which returned "Access Denied" (403)
from this machine on 2026-10-13 even with browser headers, so the HTTP call is made here
directly with a fallback base instead of through nba_api.

Every route answers 200 with ``{"success", "data", "meta"}``; upstream failures become
``success: false`` plus ``meta.message`` (and stale cached data when there is some).
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Optional

import requests
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/live", tags=["live"])

DEFAULT_BASES = (
    "https://cdn.nba.com/static/json",
    "https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA",
)
SCOREBOARD_PATH = "liveData/scoreboard/todaysScoreboard_00.json"
SCHEDULE_PATH = "staticData/scheduleLeagueV2_1.json"
BOXSCORE_PATH = "liveData/boxscore/boxscore_{game_id}.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}
HTTP_TIMEOUT = 12

TTL_LIVE = 15.0
TTL_IDLE_SCOREBOARD = 60.0
TTL_FINAL = 3600.0
TTL_PREGAME = 60.0
TTL_SCHEDULE = 600.0

_GAME_ID_RE = re.compile(r"^\d{10}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CLOCK_RE = re.compile(r"^PT(\d+)M([\d.]+)S$")


class LiveFetchError(RuntimeError):
    pass


# --------------------------------------------------------------------------- HTTP


def _bases() -> list[str]:
    raw = os.getenv("NBA_LIVE_BASE_URLS", "").strip()
    if raw:
        return [b.strip().rstrip("/") for b in raw.split(",") if b.strip()]
    return list(DEFAULT_BASES)


_preferred_base: Optional[str] = None
_session = requests.Session()


def _http_get_json(path: str) -> dict[str, Any]:
    """GET ``path`` from the first base that answers with JSON. Remembers the winner."""
    global _preferred_base
    bases = _bases()
    if _preferred_base in bases:
        bases.remove(_preferred_base)
        bases.insert(0, _preferred_base)
    errors: list[str] = []
    for base in bases:
        url = f"{base}/{path}"
        try:
            resp = _session.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        except requests.RequestException as exc:
            errors.append(f"{base}: {type(exc).__name__}")
            continue
        if resp.status_code != 200:
            errors.append(f"{base}: HTTP {resp.status_code}")
            continue
        try:
            data = resp.json()
        except ValueError:
            errors.append(f"{base}: non-JSON body")
            continue
        _preferred_base = base
        return data
    raise LiveFetchError(f"{path} unavailable ({'; '.join(errors)})")


# -------------------------------------------------------------------------- cache

_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.Lock()


def _cached(key: str, loader: Callable[[], Any], ttl_for: Callable[[Any], float]) -> tuple[Any, bool]:
    """Return ``(value, from_cache)``. On loader failure, serve stale data if any."""
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
    if hit and hit[0] > now:
        return hit[1], True
    try:
        value = loader()
    except LiveFetchError:
        if hit:
            logger.warning("live: serving stale %s", key)
            return hit[1], True
        raise
    with _cache_lock:
        _cache[key] = (now + ttl_for(value), value)
    return value, False


def clear_cache() -> None:
    global _preferred_base
    with _cache_lock:
        _cache.clear()
    _preferred_base = None


# --------------------------------------------------------------------- normalizers


def format_clock(raw: Any) -> str:
    """``PT05M46.00S`` -> ``5:46``; under a minute -> ``34.5``."""
    if not raw or not isinstance(raw, str):
        return ""
    m = _CLOCK_RE.match(raw.strip())
    if not m:
        return raw.strip()
    minutes, seconds = int(m.group(1)), float(m.group(2))
    if minutes == 0 and seconds < 60:
        if seconds == 0:
            return "0:00"
        return f"{seconds:.1f}"
    return f"{minutes}:{int(seconds):02d}"


def _minutes(raw: Any) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        m = _CLOCK_RE.match(raw.strip())
        if m:
            return round(int(m.group(1)) + float(m.group(2)) / 60.0, 1)
    return 0.0


def period_label(period: int, regulation: int = 4) -> str:
    if period <= 0:
        return ""
    if period <= regulation:
        return f"Q{period}"
    ot = period - regulation
    return "OT" if ot == 1 else f"{ot}OT"


def _state(status: Any) -> str:
    try:
        s = int(status)
    except (TypeError, ValueError):
        return "scheduled"
    return {1: "scheduled", 2: "live", 3: "final"}.get(s, "scheduled")


def _team(t: dict[str, Any]) -> dict[str, Any]:
    periods = [int(p.get("score") or 0) for p in (t.get("periods") or [])]
    return {
        "teamId": t.get("teamId"),
        "tricode": t.get("teamTricode") or "",
        "name": t.get("teamName") or "",
        "city": t.get("teamCity") or "",
        "score": int(t.get("score") or 0),
        "wins": t.get("wins"),
        "losses": t.get("losses"),
        "periods": periods,
        "timeoutsRemaining": t.get("timeoutsRemaining"),
        "inBonus": t.get("inBonus") in ("1", 1, True),
    }


def _leader(raw: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not raw or not raw.get("personId"):
        return None
    return {
        "personId": raw.get("personId"),
        "name": raw.get("name") or "",
        "points": raw.get("points"),
        "rebounds": raw.get("rebounds"),
        "assists": raw.get("assists"),
    }


def _period_text(state: str, period: int, clock: str, status_text: str, regulation: int = 4) -> str:
    if state == "final":
        return "Final" if period <= regulation else f"Final/{period_label(period, regulation)}"
    if state == "live":
        return period_label(period, regulation) or (status_text or "Live")
    return status_text or ""


def normalize_game(g: dict[str, Any], game_date: Optional[str] = None) -> dict[str, Any]:
    """Shared game shape for scoreboard, schedule and box score sources."""
    state = _state(g.get("gameStatus"))
    period = int(g.get("period") or 0)
    regulation = int(g.get("regulationPeriods") or 4)
    clock = format_clock(g.get("gameClock"))
    status_text = (g.get("gameStatusText") or "").strip()
    if state == "final" and not period:
        period = regulation
    start = g.get("gameTimeUTC") or g.get("gameDateTimeUTC")
    if start and start.startswith("1900"):
        start = g.get("gameDateTimeUTC")
    if not game_date:
        code = g.get("gameCode") or ""
        if len(code) >= 8 and code[:8].isdigit():
            game_date = f"{code[0:4]}-{code[4:6]}-{code[6:8]}"
    leaders = g.get("gameLeaders") or {}
    home = _team(g.get("homeTeam") or {})
    away = _team(g.get("awayTeam") or {})
    return {
        "gameId": g.get("gameId"),
        "date": game_date,
        "startTimeUTC": start,
        "status": int(g.get("gameStatus") or 1),
        "state": state,
        "isLive": state == "live",
        "isFinal": state == "final",
        "statusText": status_text,
        "period": period,
        "periodText": _period_text(state, period, clock, status_text, regulation),
        "clock": clock if state == "live" else "",
        "label": g.get("gameLabel") or "",
        "subLabel": g.get("gameSubLabel") or "",
        "home": home,
        "away": away,
        "leaders": {
            "home": _leader(leaders.get("homeLeaders")),
            "away": _leader(leaders.get("awayLeaders")),
        },
    }


def _schedule_date_iso(raw: str) -> Optional[str]:
    # "10/13/2026 00:00:00"
    try:
        return datetime.strptime(raw.split(" ")[0], "%m/%d/%Y").date().isoformat()
    except (ValueError, AttributeError):
        return None


# ------------------------------------------------------------------------- loaders


def get_scoreboard() -> tuple[dict[str, Any], bool]:
    def load() -> dict[str, Any]:
        raw = _http_get_json(SCOREBOARD_PATH).get("scoreboard") or {}
        day = raw.get("gameDate")
        games = [normalize_game(g, day) for g in raw.get("games") or []]
        return {"date": day, "games": games, "hasLive": any(g["isLive"] for g in games)}

    return _cached(
        "scoreboard",
        load,
        lambda v: TTL_LIVE if v.get("hasLive") else TTL_IDLE_SCOREBOARD,
    )


def get_schedule() -> tuple[dict[str, list[dict[str, Any]]], bool]:
    """``{YYYY-MM-DD: [game, ...]}`` for the whole season."""

    def load() -> dict[str, list[dict[str, Any]]]:
        ls = _http_get_json(SCHEDULE_PATH).get("leagueSchedule") or {}
        out: dict[str, list[dict[str, Any]]] = {}
        for gd in ls.get("gameDates") or []:
            day = _schedule_date_iso(gd.get("gameDate") or "")
            if not day:
                continue
            games = []
            for g in gd.get("games") or []:
                game = normalize_game(g, day)
                pl = g.get("pointsLeaders") or []
                if pl:
                    top = pl[0]
                    game["pointsLeader"] = {
                        "personId": top.get("personId"),
                        "name": f"{top.get('firstName', '')} {top.get('lastName', '')}".strip(),
                        "tricode": top.get("teamTricode"),
                        "points": top.get("points"),
                    }
                games.append(game)
            if games:
                out[day] = games
        return out

    return _cached("schedule", load, lambda _v: TTL_SCHEDULE)


def _player_row(p: dict[str, Any], tricode: str) -> dict[str, Any]:
    s = p.get("statistics") or {}
    return {
        "personId": p.get("personId"),
        "name": p.get("name") or "",
        "nameI": p.get("nameI") or "",
        "firstName": p.get("firstName") or "",
        "familyName": p.get("familyName") or "",
        "jersey": p.get("jerseyNum") or "",
        "position": p.get("position") or "",
        "teamTricode": tricode,
        "starter": p.get("starter") == "1",
        "oncourt": p.get("oncourt") == "1",
        "played": p.get("played") == "1",
        "status": p.get("status") or "",
        "notPlayingReason": p.get("notPlayingReason") or "",
        "minutes": _minutes(s.get("minutes")),
        "pts": s.get("points", 0),
        "fgm": s.get("fieldGoalsMade", 0),
        "fga": s.get("fieldGoalsAttempted", 0),
        "fg3m": s.get("threePointersMade", 0),
        "fg3a": s.get("threePointersAttempted", 0),
        "ftm": s.get("freeThrowsMade", 0),
        "fta": s.get("freeThrowsAttempted", 0),
        "oreb": s.get("reboundsOffensive", 0),
        "dreb": s.get("reboundsDefensive", 0),
        "reb": s.get("reboundsTotal", 0),
        "ast": s.get("assists", 0),
        "stl": s.get("steals", 0),
        "blk": s.get("blocks", 0),
        "tov": s.get("turnovers", 0),
        "pf": s.get("foulsPersonal", 0),
        "plusMinus": s.get("plusMinusPoints", 0),
    }


_TEAM_STAT_KEYS = {
    "fgm": "fieldGoalsMade",
    "fga": "fieldGoalsAttempted",
    "fg3m": "threePointersMade",
    "fg3a": "threePointersAttempted",
    "ftm": "freeThrowsMade",
    "fta": "freeThrowsAttempted",
    "oreb": "reboundsOffensive",
    "dreb": "reboundsDefensive",
    "reb": "reboundsTotal",
    "ast": "assists",
    "stl": "steals",
    "blk": "blocks",
    "tov": "turnoversTotal",
    "pf": "foulsPersonal",
    "teamFouls": "foulsTeam",
    "pointsInThePaint": "pointsInThePaint",
    "pointsFastBreak": "pointsFastBreak",
    "pointsSecondChance": "pointsSecondChance",
    "pointsFromTurnovers": "pointsFromTurnovers",
    "benchPoints": "benchPoints",
    "biggestLead": "biggestLead",
}


def _top(players: list[dict[str, Any]], key: str, n: int = 3) -> list[dict[str, Any]]:
    ranked = sorted((p for p in players if p["played"]), key=lambda p: p[key] or 0, reverse=True)
    return [
        {
            "personId": p["personId"],
            "name": p["name"],
            "familyName": p["familyName"],
            "teamTricode": p["teamTricode"],
            "value": p[key],
        }
        for p in ranked[:n]
    ]


def normalize_boxscore(raw: dict[str, Any]) -> dict[str, Any]:
    g = raw.get("game") or {}
    game = normalize_game(g)
    teams: dict[str, Any] = {}
    all_players: list[dict[str, Any]] = []
    for side in ("home", "away"):
        t = g.get(f"{side}Team") or {}
        tricode = t.get("teamTricode") or ""
        players = [_player_row(p, tricode) for p in t.get("players") or []]
        all_players.extend(players)
        stats = t.get("statistics") or {}
        teams[side] = {
            **game[side],
            "statistics": {k: stats.get(v) for k, v in _TEAM_STAT_KEYS.items()},
            "players": players,
        }
    return {
        "game": game,
        "teams": teams,
        "leaders": {
            "points": _top(all_players, "pts"),
            "rebounds": _top(all_players, "reb"),
            "assists": _top(all_players, "ast"),
        },
    }


def get_boxscore(game_id: str) -> tuple[dict[str, Any], bool]:
    def load() -> dict[str, Any]:
        return normalize_boxscore(_http_get_json(BOXSCORE_PATH.format(game_id=game_id)))

    def ttl(v: dict[str, Any]) -> float:
        state = v["game"]["state"]
        return TTL_FINAL if state == "final" else TTL_LIVE if state == "live" else TTL_PREGAME

    return _cached(f"box:{game_id}", load, ttl)


# ------------------------------------------------------------------------- helpers


def _ok(data: Any, **meta: Any) -> dict[str, Any]:
    return {"success": True, "data": data, "meta": {"source": _preferred_base, **meta}}


def _fail(data: Any, message: str) -> dict[str, Any]:
    logger.warning("live: %s", message)
    return {"success": False, "data": data, "meta": {"message": message}}


def _merge_today(schedule_games: list[dict[str, Any]], scoreboard_games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Scoreboard is fresher than the static schedule for the same game id."""
    by_id = {g["gameId"]: g for g in scoreboard_games}
    merged = [by_id.pop(g["gameId"], g) for g in schedule_games]
    merged.extend(by_id.values())
    return merged


def _norm_name(name: str) -> str:
    base = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z]", "", base.lower())


def _sort_games(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {"live": 0, "scheduled": 1, "final": 2}
    return sorted(games, key=lambda g: (order.get(g["state"], 3), g.get("startTimeUTC") or ""))


def _today_et() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:  # tzdata missing
        return (datetime.now(timezone.utc) - timedelta(hours=5)).date().isoformat()


# -------------------------------------------------------------------------- routes


@router.get("/scoreboard")
def live_scoreboard() -> dict[str, Any]:
    """Today's games (NBA day, ET) with score, period, clock, status."""
    try:
        sb, cached = get_scoreboard()
    except LiveFetchError as exc:
        return _fail({"date": _today_et(), "games": [], "hasLive": False}, str(exc))
    data = {**sb, "games": _sort_games(sb["games"])}
    msg = None if sb["games"] else "No NBA games scheduled today"
    return _ok(data, cached=cached, message=msg)


@router.get("/game/{game_id}")
def live_game(game_id: str) -> dict[str, Any]:
    """Box score (team totals, every player line) + top-3 PTS/REB/AST leaders."""
    if not _GAME_ID_RE.match(game_id):
        return _fail(None, f"Invalid game_id: {game_id}")
    try:
        box, cached = get_boxscore(game_id)
    except LiveFetchError as exc:
        return _fail(None, f"Box score not available yet ({exc})")
    return _ok(box, cached=cached)


def _schedule_day(day: str, schedule: dict[str, list[dict[str, Any]]], scoreboard: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    games = schedule.get(day, [])
    if scoreboard and scoreboard.get("date") == day:
        games = _merge_today(games, scoreboard["games"])
    return _sort_games(games)


@router.get("/schedule")
def live_schedule(date_: Optional[str] = Query(None, alias="date")) -> dict[str, Any]:
    """Games on one date (YYYY-MM-DD, ET). Defaults to today. Past days carry final scores."""
    day = date_ or _today_et()
    if not _DATE_RE.match(day):
        return _fail({"date": day, "games": []}, f"Invalid date: {day} (want YYYY-MM-DD)")
    try:
        schedule, cached = get_schedule()
    except LiveFetchError as exc:
        return _fail({"date": day, "games": []}, str(exc))
    scoreboard = None
    try:
        scoreboard, _ = get_scoreboard()
    except LiveFetchError:
        pass
    games = _schedule_day(day, schedule, scoreboard)
    days = sorted(schedule)
    prev_day = next((d for d in reversed(days) if d < day), None)
    next_day = next((d for d in days if d > day), None)
    return _ok(
        {"date": day, "games": games, "prevDate": prev_day, "nextDate": next_day},
        cached=cached,
        message=None if games else f"No NBA games on {day}",
    )


def _parse_players(raw: Optional[str]) -> list[tuple[str, Optional[str]]]:
    out: list[tuple[str, Optional[str]]] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        name, _, team = part.partition(":")
        out.append((name.strip(), team.strip().upper() or None))
    return out[:20]


def _next_game_for(team: str, after_day: str, schedule: dict[str, list[dict[str, Any]]], include_today: bool) -> Optional[dict[str, Any]]:
    for day in sorted(schedule):
        if day < after_day or (day == after_day and not include_today):
            continue
        for g in _sort_games(schedule[day]):
            if g["state"] != "scheduled":
                continue
            if team in (g["home"]["tricode"], g["away"]["tricode"]):
                is_home = g["home"]["tricode"] == team
                return {
                    "gameId": g["gameId"],
                    "date": day,
                    "startTimeUTC": g["startTimeUTC"],
                    "statusText": g["statusText"],
                    "opponent": g["away"]["tricode"] if is_home else g["home"]["tricode"],
                    "isHome": is_home,
                }
    return None


def _find_players(
    wanted: list[tuple[str, Optional[str]]],
    candidate_games: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Most recent box-score line per wanted name, scanning ``candidate_games`` in order."""
    if not wanted or not candidate_games:
        return {}

    def fetch(gid: str) -> Optional[dict[str, Any]]:
        try:
            return get_boxscore(gid)[0]
        except LiveFetchError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        boxes = list(pool.map(fetch, [g["gameId"] for g in candidate_games]))

    keys = {_norm_name(n): n for n, _ in wanted}
    found: dict[str, dict[str, Any]] = {}
    dnp: dict[str, dict[str, Any]] = {}  # fallback when the player sat every scanned game
    for box in boxes:
        if not box:
            continue
        game = box["game"]
        for side, other in (("home", "away"), ("away", "home")):
            for p in box["teams"][side]["players"]:
                key = _norm_name(p["name"])
                if key not in keys or keys[key] in found:
                    continue
                bucket = found if (p["played"] or game["state"] == "live") else dnp
                if keys[key] not in bucket:
                    bucket[keys[key]] = {
                        **p,
                        "gameId": game["gameId"],
                        "date": game["date"],
                        "state": game["state"],
                        "periodText": game["periodText"],
                        "clock": game["clock"],
                        "opponentTricode": box["teams"][other]["tricode"],
                        "isHome": side == "home",
                    }
    for name, line in dnp.items():
        found.setdefault(name, line)
    return found


@router.get("/board")
def live_board(
    past_days: int = Query(3, ge=0, le=10),
    players: Optional[str] = Query(None, description="Comma list of 'Full Name[:TEAM]' to track"),
) -> dict[str, Any]:
    """Everything the right-rail live board needs in one call.

    today      — today's games (scoreboard merged over schedule)
    pastDays   — the last ``past_days`` dates that had games, newest first
    upcoming   — the next date with games (useful when today is empty)
    players    — latest box line per tracked player + their team's next game
    """
    empty = {"today": {"date": _today_et(), "games": [], "hasLive": False}, "pastDays": [], "upcoming": None, "players": []}
    scoreboard = None
    sb_error = None
    try:
        scoreboard, _ = get_scoreboard()
    except LiveFetchError as exc:
        sb_error = str(exc)
    try:
        schedule, _ = get_schedule()
    except LiveFetchError as exc:
        schedule = {}
        if sb_error:
            return _fail(empty, f"{sb_error}; {exc}")

    today = (scoreboard or {}).get("date") or _today_et()
    today_games = _schedule_day(today, schedule, scoreboard)
    days = sorted(schedule)
    past = [d for d in reversed(days) if d < today][:past_days]
    past_payload = [{"date": d, "games": _sort_games(schedule[d])} for d in past]
    nxt = next((d for d in days if d > today), None)
    upcoming = {"date": nxt, "games": _sort_games(schedule[nxt])} if nxt else None

    tracked = _parse_players(players)
    player_payload: list[dict[str, Any]] = []
    if tracked:
        candidates = [g for g in today_games if g["state"] != "scheduled"]
        for day in past_payload:
            candidates.extend(g for g in day["games"] if g["state"] == "final")
        found = _find_players(tracked, candidates)
        for name, hint in tracked:
            line = found.get(name)
            team = (line or {}).get("teamTricode") or hint
            plays_today = bool(team) and any(
                team in (g["home"]["tricode"], g["away"]["tricode"]) for g in today_games
            )
            player_payload.append(
                {
                    "query": name,
                    "found": line is not None,
                    "teamTricode": team,
                    "playsToday": plays_today,
                    "line": line,
                    "nextGame": _next_game_for(team, today, schedule, include_today=True) if team else None,
                }
            )

    data = {
        "today": {"date": today, "games": today_games, "hasLive": any(g["isLive"] for g in today_games)},
        "pastDays": past_payload,
        "upcoming": upcoming,
        "players": player_payload,
    }
    return _ok(data, message=sb_error)
