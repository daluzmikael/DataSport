"""Measure real per-question token spend, then project across model tiers."""
import os, sys, json, io
sys.path.insert(0, r"C:\Users\mikae\Coder\DataSport\DataSport\backend")
os.chdir(r"C:\Users\mikae\Coder\DataSport\DataSport\backend")
import tiktoken
enc = tiktoken.get_encoding("o200k_base")
tok = lambda s: len(enc.encode(s or ""))

from Interpreter.router_plan import table_catalog_prompt_text
from Interpreter.router import _ROUTER_SYSTEM, _FEW_SHOT
from Executer.data_backend import get_connection
from Analyzer.aggregates import compute_bundle_aggregates

conn = get_connection()

router_prompt = tok(_ROUTER_SYSTEM) + tok(_FEW_SHOT) + tok(table_catalog_prompt_text())
ROUTER_OUT = 220   # observed JSON plan size
ANALYST_OUT = 420  # observed answer length

FOCUS = ["PTS","REB","AST","MIN","GP","FG_PCT","FG3_PCT","STL","BLK","TOV","PLUS_MINUS"]

SCENARIOS = [
    ("single season lookup", "SELECT * FROM player_season_stats WHERE PLAYER_NAME='LeBron James' AND season='2023-24' AND per_mode='PerGame' AND season_type='Regular Season'"),
    ("career season span (23 rows)", "SELECT * FROM player_season_stats WHERE PLAYER_NAME='LeBron James' AND per_mode='Totals' AND season_type='Regular Season'"),
    ("leaderboard top 10", "SELECT * FROM player_season_stats WHERE season='2023-24' AND per_mode='PerGame' AND season_type='Regular Season' ORDER BY PTS DESC LIMIT 10"),
    ("game-log split (32 rows)", "SELECT * FROM player_game_logs WHERE PLAYER_NAME='LeBron James' AND season_type='Regular Season' AND MATCHUP ILIKE '%CHI%' AND MATCHUP ILIKE '%vs.%'"),
    ("game-log split (473 rows)", "SELECT * FROM player_game_logs WHERE PLAYER_NAME='Stephen Curry' AND season_type='Regular Season' AND MIN>35"),
    ("full career game log (1622)", "SELECT * FROM player_game_logs WHERE PLAYER_NAME='LeBron James' AND season_type='Regular Season'"),
]

ANALYST_SYS = 1500  # measured analyst system prompt

rows = []
for label, sql in SCENARIOS:
    df = conn.execute(sql).fetchdf()
    keep = [c for c in df.columns if c in FOCUS or c.lower() in
            ("season","player_name","game_date","matchup","wl","team_abbreviation","season_type","per_mode")]
    narrow = df[keep] if keep else df
    body = narrow.head(1200).to_string(index=False)
    agg = compute_bundle_aggregates({"b": df}, FOCUS)
    analyst_in = ANALYST_SYS + tok(body) + tok(agg)
    rows.append((label, len(df), router_prompt, analyst_in))

# $ per 1M tokens (input, output). gpt-5.5 pricing is a planning estimate.
MODELS = [
    ("gpt-4o-mini",        0.15,  0.60),
    ("gpt-5.4-mini (now)", 0.25,  2.00),
    ("gpt-5.5 (est.)",     1.25, 10.00),
    ("Sonnet 5",           3.00, 15.00),
]

print(f"router prompt = {router_prompt:,} tokens/call (system + few-shot + live catalog)\n")
print(f"{'scenario':30} {'rows':>6} {'in-tok':>9}  " + "  ".join(f"{m[0]:>18}" for m in MODELS))
print("-" * 118)
totals = {m[0]: 0.0 for m in MODELS}
for label, n, r_in, a_in in rows:
    total_in = r_in + a_in
    total_out = ROUTER_OUT + ANALYST_OUT
    cells = []
    for name, pin, pout in MODELS:
        cost = total_in / 1e6 * pin + total_out / 1e6 * pout
        totals[name] += cost
        cells.append(f"${cost:>17.5f}")
    print(f"{label:30} {n:>6,} {total_in:>9,}  " + "  ".join(cells))

print("-" * 118)
n = len(rows)
print(f"{'AVERAGE per question':30} {'':>6} {'':>9}  " +
      "  ".join(f"${totals[m[0]]/n:>17.5f}" for m in MODELS))
print()
for name, _, _ in MODELS:
    avg = totals[name] / n
    print(f"{name:22} avg ${avg:.5f}/question   100 q = ${avg*100:6.2f}   1,000 q = ${avg*1000:7.2f}")
