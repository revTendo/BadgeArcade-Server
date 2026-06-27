import logging
import sqlite3
import threading
import time
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection

import config

log = logging.getLogger(__name__)

_mongo_client = None
_nex_accounts: Optional[Collection] = None

_sqlite_path: Optional[str] = None
_write_lock  = threading.Lock()


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
                pid   INTEGER PRIMARY KEY,
                urls  TEXT,
                ip    TEXT,
                port  TEXT
            );

            CREATE TABLE IF NOT EXISTS free_play_data (
                data_id      INTEGER PRIMARY KEY,
                owner_id     INTEGER,
                meta_binary  BLOB,
                created_time INTEGER,
                updated_time INTEGER,
                period       INTEGER,
                flag         INTEGER,
                referred_time INTEGER
            );

            CREATE TABLE IF NOT EXISTS user_play_info (
                data_id INTEGER PRIMARY KEY,
                pid     INTEGER,
                slot    INTEGER,
                version INTEGER
            );
        """)
        conn.execute("DELETE FROM sessions")
        conn.commit()
    log.info("SQLite ready at %s", _sqlite_path)


def _conn():
    return sqlite3.connect(_sqlite_path, check_same_thread=False)


def get_nex_account_by_pid(pid: int) -> Optional[dict]:
    try:
        return _nex_accounts.find_one({"pid": pid})
    except Exception:
        log.exception("MongoDB error get_nex_account_by_pid pid=%d", pid)
        return None


def get_nex_account_by_username(username: str) -> Optional[dict]:
    try:
        return _nex_accounts.find_one({"username": username})
    except Exception:
        log.exception("MongoDB error get_nex_account_by_username %r", username)
        return None


def create_nex_account(pid: int, username: str, password: str = "nexpassword") -> dict:
    doc = {"pid": pid, "username": username, "password": password}
    try:
        _nex_accounts.update_one({"pid": pid}, {"$setOnInsert": doc}, upsert=True)
        log.info("Auto-created nex account pid=%d username=%r", pid, username)
    except Exception:
        log.exception("MongoDB error create_nex_account pid=%d", pid)
    return doc


def get_or_create_nex_account(username: str) -> Optional[dict]:
    account = get_nex_account_by_username(username)
    if account is not None:
        return account
    # 3DS usernames are the PID rendered as a string; use it as the PID.
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
