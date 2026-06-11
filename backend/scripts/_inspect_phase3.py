import pandas as pd

gc = pd.read_parquet("data/staging/game_context.parquet")
gid = "0022401106"
sub = gc[gc["game_id"] == gid]
d4 = sub[sub["dataset"] == "4"]
d6 = sub[sub["dataset"] == "6"].iloc[0]
print("=== dataset 6 (game header) ===")
for k in d6.index:
    v = d6[k]
    if v not in (None, "", "nan") and str(v) != "nan":
        print(f"  {k}: {v}")

print("\n=== dataset 4 (line score) ===")
print(d4[["teamTricode", "period1Score", "period2Score", "period3Score", "period4Score", "score"]].to_string())
