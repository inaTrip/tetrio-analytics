"""Run the example queries in warehouse/queries.sql and print the results.

Run from the repository root:  python -m notebooks.explore_warehouse
"""
import duckdb

from src import settings

con = duckdb.connect(str(settings.WAREHOUSE_PATH), read_only=True)
sql = (settings.WAREHOUSE_SQL_DIR / "queries.sql").read_text(encoding="utf-8")

# Split the file on ";" and run each query that is not only comments.
for statement in sql.split(";"):
    code = "\n".join(l for l in statement.splitlines() if not l.strip().startswith("--"))
    if not code.strip():
        continue
    title = next((l.strip("- ") for l in statement.splitlines()
                  if l.strip().startswith("-- Q")), "Query")
    print(f"\n=== {title} ===")
    print(con.sql(code))
con.close()
