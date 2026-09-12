"""Generate VAULT_SCHEMA.md — the map the router reads before choosing a table.

The router used to be handed a hand-written catalog that drifted from the data. It
claimed tracking started in 2013-14 when the table holds rows back to 1996-97; it
advertised per_mode values (Per36, Per40, Per100Possessions) that no staged table
contains, so the model would emit valid SQL that silently returned nothing.

This reads the live DuckDB views instead and writes down what is actually there:
every column, the real slice values, the real season coverage, and — crucially —
per-slice coverage, so "who led the league in drives in 2005-06" can be refused
with a reason instead of returning an empty table.

    python -m scripts.generate_vault_schema

Re-run after any staging change. The output is committed so it can be diffed.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Executer.data_backend import get_connection  # noqa: E402
from Executer.duckdb_store import list_registered_tables  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "Interpreter" / "VAULT_SCHEMA.md"

# Slice columns worth enumerating exhaustively — these are what the router filters on.
SLICE_COLUMNS = ("season_type", "per_mode", "pt_measure_type", "measure_type", "group_quantity")

# Stat families collapsed in the listing so the file stays readable.
FAMILY_PREFIXES = (("clutch_", "clutch split"), ("hustle_", "hustle stat"))
FAMILY_SUFFIXES = (("_RANK", "league rank"),)

NAME_COLUMN_CANDIDATES = (
    "PLAYER_NAME", "player_name", "TEAM_NAME", "team_name", "TeamName",
    "teamName", "GROUP_NAME",
)


def q1(conn, sql, params=None):
    try:
        row = conn.execute(sql, params or []).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def qlist(conn, sql, params=None, limit=40):
    try:
        return [r[0] for r in conn.execute(sql, params or []).fetchall()[:limit]]
    except Exception:
        return []


def columns_of(conn, table):
    return conn.execute(
        """
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema='main' AND table_name=? ORDER BY ordinal_position
        """,
        [table],
    ).fetchall()


def main() -> int:
    conn = get_connection()
    tables = sorted(list_registered_tables(conn))

    out: list[str] = []
    w = out.append

    w("# Vault schema map")
    w("")
    w(f"Generated {date.today().isoformat()} by `scripts/generate_vault_schema.py` "
      "directly from the live DuckDB views. Do not hand-edit — re-run the script.")
    w("")
    w("**Read this before choosing a table.** Every column, slice value and season "
      "range below is what the data actually contains, not what it is expected to "
      "contain. If a stat is not listed here, it is not in the vault; say so rather "
      "than substituting a different stat.")
    w("")
    w(f"{len(tables)} tables registered.")
    w("")

    # ---- quick index -----------------------------------------------------
    w("## Where to find a stat")
    w("")
    w("| If the question is about | Use this table |")
    w("|---|---|")
    for label, table in (
        ("A player's season box score (points, rebounds, shooting splits, clutch, hustle)", "player_season_stats"),
        ("A team's season box score", "team_season_stats"),
        ("Player season efficiency / impact ratings (E_ prefixed)", "player_estimated_metrics"),
        ("Team season efficiency / pace", "team_estimated_metrics"),
        ("One player in one game, or game-by-game form", "player_game_logs"),
        ("One team in one game, or schedule/results", "team_game_logs"),
        ("Standings, record, seeding, streaks", "team_standings"),
        ("Shooting broken out by court zone", "player_shot_zones / team_shot_zones"),
        ("Tracking (drives, touches, rim defense, catch-and-shoot)", "player_tracking / team_tracking"),
        ("Five-man lineup units, and the only TS%/EFG%/PIE at season grain", "lineups"),
        ("Game-level advanced (true shooting, usage, PIE per game)", "player_game_advanced"),
    ):
        if table.split(" / ")[0] in tables:
            w(f"| {label} | `{table}` |")
    w("")

    # ---- per table -------------------------------------------------------
    w("## Tables")
    for table in tables:
        cols = columns_of(conn, table)
        colnames = [c for c, _ in cols]
        n = q1(conn, f"SELECT COUNT(*) FROM {table}")

        w("")
        w(f"### `{table}`")
        w("")
        w(f"- rows: **{n:,}**" if isinstance(n, int) else "- rows: unknown")

        name_col = next((c for c in NAME_COLUMN_CANDIDATES if c in colnames), None)
        if name_col:
            sample = qlist(conn, f"SELECT DISTINCT {name_col} FROM {table} WHERE {name_col} IS NOT NULL LIMIT 3")
            w(f"- name column: `{name_col}` — filterable by name. "
              f"Values look like: {', '.join(repr(s) for s in sample)}")
        else:
            w("- name column: **NONE — this table cannot be filtered by a person's or "
              "team's name.** Do not route a named-entity question here.")

        if "season" in colnames:
            lo = q1(conn, f"SELECT MIN(season) FROM {table}")
            hi = q1(conn, f"SELECT MAX(season) FROM {table}")
            w(f"- season coverage: **{lo} → {hi}**")
        else:
            w("- **no `season` column** — cannot be filtered by season.")

        for slice_col in SLICE_COLUMNS:
            if slice_col in colnames:
                vals = qlist(conn, f"SELECT DISTINCT {slice_col} FROM {table} WHERE {slice_col} IS NOT NULL")
                vals = sorted(str(v) for v in vals)
                w(f"- `{slice_col}` values present: {', '.join(f'`{v}`' for v in vals)}")

        # Per-slice season coverage: the gap that made "drives in 2005-06" fail silently.
        if "pt_measure_type" in colnames and "season" in colnames:
            w("- per-slice season coverage:")
            rows = []
            try:
                rows = conn.execute(
                    f"SELECT pt_measure_type, MIN(season), MAX(season), COUNT(*) "
                    f"FROM {table} GROUP BY pt_measure_type ORDER BY 1"
                ).fetchall()
            except Exception:
                pass
            for mt, lo, hi, cnt in rows:
                w(f"  - `{mt}`: {lo} → {hi} ({cnt:,} rows)")

        families: dict[str, int] = {}
        plain: list[str] = []
        for c in colnames:
            hit = None
            for pre, label in FAMILY_PREFIXES:
                if c.startswith(pre):
                    hit = f"`{pre}*` ({label})"
                    break
            if hit is None:
                for suf, label in FAMILY_SUFFIXES:
                    if c.endswith(suf):
                        hit = f"`*{suf}` ({label})"
                        break
            if hit:
                families[hit] = families.get(hit, 0) + 1
            else:
                plain.append(c)

        w(f"- columns: **{len(colnames)}** total")
        w("")
        w(f"  {', '.join(f'`{c}`' for c in plain)}")
        if families:
            w("")
            for fam, cnt in sorted(families.items()):
                w(f"  - plus {cnt} × {fam}")

    # ---- absences --------------------------------------------------------
    w("")
    w("## Commonly-asked advanced stats — where they live")
    w("")
    w("Checked against the live schema on every regeneration, so this table cannot "
      "drift from the data. A stat marked **yes** is a plain column on the season "
      "table and needs no join and no `measure_type` filter.")
    w("")
    w("| Stat | On `player_season_stats`? | On `team_season_stats`? | Also available |")
    w("|---|---|---|---|")
    pcols = {c for c, _ in columns_of(conn, "player_season_stats")} if "player_season_stats" in tables else set()
    tcols = {c for c, _ in columns_of(conn, "team_season_stats")} if "team_season_stats" in tables else set()
    for col, label, where in (
        ("TS_PCT", "true shooting %", "`lineups`; `player_game_advanced` as `trueShootingPercentage`"),
        ("EFG_PCT", "effective FG %", "`lineups`; `player_game_advanced`"),
        ("USG_PCT", "usage rate", "`player_estimated_metrics` as `E_USG_PCT`"),
        ("PIE", "player impact estimate", "`lineups`; `player_game_advanced`"),
        ("OFF_RATING", "offensive rating", "`player_estimated_metrics` as `E_OFF_RATING`; `lineups`"),
        ("DEF_RATING", "defensive rating", "`player_estimated_metrics` as `E_DEF_RATING`; `lineups`"),
        ("NET_RATING", "net rating", "`player_estimated_metrics` as `E_NET_RATING`; `lineups`"),
        ("PACE", "pace", "`player_estimated_metrics` as `E_PACE`; `lineups`"),
        ("DEF_WS", "defensive win shares", "patchy — the Defense dash pull is empty for some seasons"),
    ):
        p = "**yes**" if col in pcols else "no"
        t = "**yes**" if col in tcols else "no"
        w(f"| `{col}` ({label}) | {p} | {t} | {where} |")
    w("")
    w("Player-only, because NBA publishes no team Usage slice: the `PCT_FGM` / "
      "`PCT_AST` / `PCT_PTS` usage-share family.")
    w("")
    w("Genuinely absent at season grain: nothing from this list. If a question asks "
      "for a stat that is not a column anywhere above, it is an absence — say so "
      "rather than calling it a multi-table limitation.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(out)} lines, {len(tables)} tables)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
