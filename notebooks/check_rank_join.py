"""Check how replays could map to rank tiers via TR."""
import pandas as pd

tl = pd.read_csv("data/raw/tl_data/tl-data-09-2023.csv")
ranges = tl.groupby("rank")["tr"].agg(["min", "max", "count"]).sort_values("min")
print("TR range per rank (Sep 2023):")
print(ranges.to_string())

games = (pd.read_csv("data/raw/replays/data.csv", usecols=["game_id", "rating", "won"])
           .drop_duplicates("game_id"))
print(f"\nDistinct games: {len(games):,}")
print(games["rating"].describe().to_string())
