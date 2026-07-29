import logging
import sqlite3
import threading
import time
from nex.crypto import make_datetime_now
from typing import Optional
from pymongo import MongoClient
from pymongo.collection import Collection
import os
import config

log = logging.getLogger(__name__)

_mongo_client = None
_nex_accounts: Optional[Collection] = None
_sqlite_path: Optional[str] = None
_write_lock = threading.Lock()

def init_mongo():
    global _mongo_client, _nex_accounts
    uri = config.mongo_uri()
    _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    _mongo_client.admin.command("ping")
    log.info("MongoDB connected")
    _nex_accounts = _mongo_client["pretendo"]["nexaccounts"]

def init_sqlite():
    global _sqlite_path
    _sqlite_path = config.sqlite_path()
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                pid INTEGER PRIMARY KEY,
                urls TEXT,
                ip TEXT,
                port TEXT
            );
            
            CREATE TABLE IF NOT EXISTS user_play_info (
                data_id INTEGER,
                pid INTEGER,
                slot INTEGER,
                version INTEGER DEFAULT 0,
                PRIMARY KEY (data_id, pid, slot)
            );
            
            CREATE TABLE IF NOT EXISTS free_play_data (
                data_id INTEGER PRIMARY KEY,
                owner_id INTEGER,
                meta_binary BLOB,
                created_time INTEGER,
                updated_time INTEGER,
                period INTEGER,
                flag INTEGER,
                referred_time INTEGER
            );
            
            CREATE INDEX IF NOT EXISTS idx_free_play_owner 
            ON free_play_data(owner_id);
        """)
        conn.execute("DELETE FROM sessions")
        conn.commit()
    log.info("SQLite ready at %s", _sqlite_path)

def _conn():
    return sqlite3.connect(_sqlite_path, check_same_thread=False)

def _mysql_conn():
    import pymysql
    return pymysql.connect(
        unix_socket=os.getenv("ACCOUNTS_MYSQL_SOCKET", "/var/run/mysqld/mysqld.sock"),
        user=os.getenv("ACCOUNTS_MYSQL_USER", "revtendoaccounts"),
        password=os.getenv("ACCOUNTS_MYSQL_PASSWORD", ""),
        database=os.getenv("ACCOUNTS_MYSQL_DATABASE", "revtendoid"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

def get_nex_account_by_pid(pid: int) -> Optional[dict]:
    try:
        conn = _mysql_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT pid, password FROM nex_accounts WHERE pid = %s LIMIT 1", (pid,))
            row = cur.fetchone()
        conn.close()
        if row:
            return {"pid": int(row["pid"]), "username": str(row["pid"]), "password": row["password"]}
        return None
    except Exception:
        log.exception("MySQL error get_nex_account_by_pid pid=%d", pid)
        return None

def get_nex_account_by_username(username: str) -> Optional[dict]:
    try:
        pid = int(username)
    except (TypeError, ValueError):
        log.warning("username %r is not numeric", username)
        return None
    return get_nex_account_by_pid(pid)

def create_nex_account(pid: int, username: str, password: str = "nexpassword") -> dict:
    try:
        conn = _mysql_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT IGNORE INTO nex_accounts (pid, password) VALUES (%s, %s)",
                (pid, password)
            )
        conn.close()
        log.info("Ensured nex account pid=%d", pid)
    except Exception:
        log.exception("MySQL error create_nex_account pid=%d", pid)
    return {"pid": pid, "username": username, "password": password}

def get_or_create_nex_account(username: str) -> Optional[dict]:
    account = get_nex_account_by_username(username)
    if account is not None:
        return account
    try:
        pid = int(username)
    except (TypeError, ValueError):
        log.warning("Cannot auto-create account: username %r is not numeric", username)
        return None
    return create_nex_account(pid, username)

def session_exists(pid: int) -> bool:
    with _conn() as conn:
        row = conn.execute("SELECT 1 FROM sessions WHERE pid=?", (pid,)).fetchone()
        return row is not None

def add_session(pid: int, urls: list, ip: str, port: str):
    with _write_lock, _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions(pid,urls,ip,port) VALUES(?,?,?,?)",
            (pid, ",".join(urls), ip, port)
        )
        conn.commit()
    log.debug("Session added pid=%d", pid)

def update_session(pid: int, urls: list, ip: str, port: str):
    with _write_lock, _conn() as conn:
        conn.execute(
            "UPDATE sessions SET urls=?,ip=?,port=? WHERE pid=?",
            (",".join(urls), ip, port, pid)
        )
        conn.commit()
    log.debug("Session updated pid=%d", pid)

def delete_session(pid: int):
    with _write_lock, _conn() as conn:
        conn.execute("DELETE FROM sessions WHERE pid=?", (pid,))
        conn.commit()
    log.debug("Session deleted pid=%d", pid)

def get_persistence_info(owner_id: int, slot: int) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT data_id FROM user_play_info WHERE pid=? AND slot=?",
            (owner_id, slot)
        ).fetchone()
        return int(row[0]) if row else 0

def get_version_by_data_id(data_id: int) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT version FROM user_play_info WHERE data_id=?", (data_id,)
        ).fetchone()
        return int(row[0]) if row else 0

def get_free_play_data_by_owner(owner_id: int) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT data_id,meta_binary,created_time,updated_time,period,flag,referred_time "
            "FROM free_play_data WHERE owner_id=?", (owner_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "data_id":       int(row[0]),
            "meta_binary":   bytes(row[1]) if row[1] else b"",
            "created_time":  int(row[2]),
            "updated_time":  int(row[3]),
            "period":        int(row[4]),
            "flag":          int(row[5]),
            "referred_time": int(row[6]),
        }

def get_free_play_data_by_data_id(data_id: int) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT data_id,meta_binary,created_time,updated_time,period,flag,referred_time "
            "FROM free_play_data WHERE data_id=?", (data_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "data_id":       int(row[0]),
            "meta_binary":   bytes(row[1]) if row[1] else b"",
            "created_time":  int(row[2]),
            "updated_time":  int(row[3]),
            "period":        int(row[4]),
            "flag":          int(row[5]),
            "referred_time": int(row[6]),
        }

def get_data_id_for_owner_slot(owner_id, slot):
    with _conn() as conn:
        row = conn.execute(
            "SELECT data_id FROM user_play_info WHERE pid=? AND slot=?",
            (owner_id, slot)
        ).fetchone()
        return int(row[0]) if row else None

def save_free_play_data(owner_id, slot, meta_binary, period, flag):
    now = make_datetime_now()
    with _write_lock, _conn() as conn:
        row = conn.execute(
            "SELECT data_id FROM user_play_info WHERE pid=? AND slot=?",
            (owner_id, slot)
        ).fetchone()
        if row:
            data_id = int(row[0])
            conn.execute(
                "UPDATE free_play_data SET meta_binary=?,updated_time=?,period=?,flag=? "
                "WHERE data_id=?",
                (meta_binary, now, period, flag, data_id)
            )
        else:
            data_id = owner_id & 0xFFFFFFFF
            conn.execute(
                "INSERT OR REPLACE INTO free_play_data"
                "(data_id,owner_id,meta_binary,created_time,updated_time,period,flag,referred_time)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (data_id, owner_id, meta_binary, now, now, period, flag, now)
            )
            conn.execute(
                "INSERT OR REPLACE INTO user_play_info(data_id,pid,slot,version) VALUES(?,?,?,1)",
                (data_id, owner_id, slot)
            )
        conn.commit()
    log.debug("Saved free_play_data data_id=%d owner=%d slot=%d (%d bytes)",
              data_id, owner_id, slot, len(meta_binary))
    return data_id

def insert_free_play_data(data_id, owner_id, meta_binary, created_time, period, flag):
    with _write_lock, _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO free_play_data"
            "(data_id,owner_id,meta_binary,created_time,updated_time,period,flag,referred_time)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (data_id, owner_id, meta_binary, created_time, created_time, period, flag, created_time)
        )
        conn.commit()
    log.debug("Inserted free_play_data data_id=%d owner=%d", data_id, owner_id)

def insert_user_play_info(data_id, pid, slot):
    with _write_lock, _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_play_info(data_id,pid,slot,version) VALUES(?,?,?,0)",
            (data_id, pid, slot)
        )
        conn.commit()
    log.debug("Inserted user_play_info data_id=%d pid=%d slot=%d", data_id, pid, slot)

def update_free_play_meta_binary(data_id, meta_binary, updated_time):
    with _write_lock, _conn() as conn:
        conn.execute(
            "UPDATE free_play_data SET meta_binary=?,updated_time=? WHERE data_id=?",
            (meta_binary, updated_time, data_id)
        )
        conn.commit()
    log.debug("Updated meta_binary data_id=%d", data_id)

def update_play_info_version(data_id, version):
    with _write_lock, _conn() as conn:
        conn.execute(
            "UPDATE user_play_info SET version=? WHERE data_id=?",
            (version, data_id)
        )
        conn.commit()
    log.debug("Updated version=%d data_id=%d", version, data_id)
