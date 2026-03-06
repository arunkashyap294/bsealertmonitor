"""
debug_fetch2.py — Raw BSE API call with explicit dates, output to file
"""
from datetime import datetime, timedelta
from bse import BSE
import json

SCRIPCODE = "500295"  # Vedanta

from_dt = datetime.now() - timedelta(hours=36)
to_dt = datetime.now()

with BSE(download_folder="./downloads") as bse:
    response = bse.announcements(
        scripcode=SCRIPCODE,
        from_date=from_dt,
        to_date=to_dt,
    )

table = response.get("Table", [])
table1 = response.get("Table1", [])

output = {
    "query": {
        "from": from_dt.strftime('%Y-%m-%d %H:%M'),
        "to": to_dt.strftime('%Y-%m-%d %H:%M'),
        "scripcode": SCRIPCODE,
    },
    "total_rows_reported": table1,
    "table_count": len(table),
    "items": table[:10],  # first 10
}

with open("debug_output.json", "w") as f:
    json.dump(output, f, indent=2, default=str)

print(f"Done. Table count={len(table)}, written to debug_output.json")
