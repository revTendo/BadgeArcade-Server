
import os
import sqlite3
import config

config.load()
path = config.sqlite_path()

conn = sqlite3.connect(path)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT fpd.data_id, fpd.owner_id, upi.slot, fpd.updated_time "
    "FROM free_play_data fpd JOIN user_play_info upi ON fpd.data_id = upi.data_id "
    "ORDER BY fpd.owner_id, upi.slot, fpd.updated_time DESC"
).fetchall()

keep = {}
delete_ids = []
for r in rows:
    key = (r["owner_id"], r["slot"])
    if key not in keep:
        keep[key] = r["data_id"]
    else:
        delete_ids.append(r["data_id"])

print(f"Found {len(rows)} saves; keeping {len(keep)}, deleting {len(delete_ids)} duplicates.")

for did in delete_ids:
    conn.execute("DELETE FROM free_play_data WHERE data_id=?", (did,))
    conn.execute("DELETE FROM user_play_info WHERE data_id=?", (did,))

for (owner, slot), did in keep.items():
    conn.execute("UPDATE user_play_info SET version=1 WHERE data_id=?", (did,))
    print(f"  kept owner={owner} slot={slot} data_id={did}")

conn.commit()
conn.close()
print("Cleanup done.")
