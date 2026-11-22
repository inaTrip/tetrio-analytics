"""Quick profiling of the raw datasets to validate them for Checkpoint 1."""
from pathlib import Path
import pandas as pd

RAW = Path("data/raw")

def profile(path: Path) -> None:
    """Print the key facts of one tabular file."""
    if path.suffix == ".csv":
        df = pd.read_csv(path)
    elif path.suffix == ".json":
        try:
            df = pd.read_json(path)
        except ValueError:
            print(f"\n=== {path} === (nested JSON, inspect manually)")
            return
    else:
        return
    print(f"\n=== {path} ===")
    print(f"Rows: {len(df):,}   Columns: {df.shape[1]}   "
          f"Size: {path.stat().st_size / 1e6:.1f} MB")
    print("\nColumns and types:")
    print(df.dtypes.to_string())
    nulls = (df.isna().mean() * 100).round(1)
    print("\n% nulls per column (only > 0):")
    print(nulls[nulls > 0].to_string() if (nulls > 0).any() else "none")
    print(f"\nDuplicate rows: {df.duplicated().sum():,}")
    print("\nFirst rows:")
    print(df.head(3).to_string())

files = sorted(RAW.rglob("*"))
print("Files found:", *[f for f in files if f.is_file()], sep="\n  ")
for f in files:
    profile(f)
