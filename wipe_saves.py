
import os
import sqlite3
import config

config.load()
db_path = config.sqlite_path()
storage = config.storage_path()

conn = sqlite3.connect(db_path)
n1 = conn.execute("SELECT COUNT(*) FROM free_play_data").fetchone()[0]
n2 = conn.execute("SELECT COUNT(*) FROM user_play_info").fetchone()[0]
conn.execute("DELETE FROM free_play_data")
conn.execute("DELETE FROM user_play_info")
conn.commit()
conn.close()
print(f"Deleted {n1} free_play_data rows and {n2} user_play_info rows.")

removed = 0
if os.path.isdir(storage):
    for fn in os.listdir(storage):
        fp = os.path.join(storage, fn)
        if os.path.isfile(fp):
            os.remove(fp)
            removed += 1
print(f"Removed {removed} stored save files from {storage}.")
print("Wipe done. The game will create a fresh save on next play.")
