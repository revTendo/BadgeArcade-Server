import os
import sys
import logging
import threading

log = logging.getLogger("shopdeck.bootstrap")

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

_done = False

def _connect_params():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shopdeck.settings")
    from django.conf import settings
    db = settings.DATABASES["default"]
    params = {
        "user": db.get("USER") or "root",
        "passwd": db.get("PASSWORD") or "",
        "charset": "utf8mb4",
    }
    opts = db.get("OPTIONS", {})
    if opts.get("unix_socket"):
        params["unix_socket"] = opts["unix_socket"]
    else:
        params["host"] = db.get("HOST") or "127.0.0.1"
        params["port"] = int(db.get("PORT") or 3306)
    return db.get("NAME", "eshop"), params

def create_database():
    import MySQLdb
    name, params = _connect_params()
    conn = MySQLdb.connect(**params)
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci" % name
        )
        conn.commit()
        log.info("Database '%s' is ready", name)
    finally:
        conn.close()

def migrate_and_collect():
    import django
    from django.core.management import call_command
    django.setup()
    call_command("makemigrations", "shopdeckdb", interactive=False, verbosity=0)
    call_command("migrate", interactive=False, verbosity=0)
    try:
        call_command("collectstatic", interactive=False, verbosity=0)
    except Exception:
        log.exception("collectstatic skipped")

def _ensure_impl():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shopdeck.settings")
    try:
        create_database()
    except Exception:
        log.exception("Could not create/verify MySQL database")
        raise
    migrate_and_collect()

def ensure(force=False):
    global _done
    if _done and not force:
        return
    error = {}

    def _runner():
        try:
            _ensure_impl()
        except Exception as exc:
            error["exc"] = exc

    t = threading.Thread(target=_runner, name="shopdeck-bootstrap")
    t.start()
    t.join()
    if "exc" in error:
        raise error["exc"]
    _done = True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure()
    print("Shopdeck database bootstrap complete.")
