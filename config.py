import logging
import os
from dotenv import load_dotenv

log = logging.getLogger(__name__)

def _require(name):
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def load():
    if load_dotenv():
        log.debug("Loaded .env")
    else:
        log.debug("No .env, using environment")

ACCESS_KEY          = "82d5962d"
NEX_VERSION         = 30716
PRUDP_VERSION       = 1
PRUDP_MINOR_VERSION = 3
KERBEROS_KEY_SIZE   = 32

AUTH_PORT           = 59400
SECURE_PORT         = 59401

def kerberos_password():   return _require("KERBEROS_PASSWORD")
def secure_server_location(): return _require("SECURE_SERVER_LOCATION")
def secure_server_port():  return os.getenv("SECURE_SERVER_PORT", str(SECURE_PORT))
def mongo_uri():           return _require("MONGO_URI")

def sqlite_path():         return os.getenv("SQLITE_PATH", "badge_arcade.db")
def storage_path():        return os.getenv("STORAGE_PATH", "datastore_files")
def file_server_port():    return int(os.getenv("FILE_SERVER_PORT", "8080"))

PRUDP_RESEND_LIMIT = 3
PRUDP_SUPPORTED_FUNCTIONS = 0
PRUDP_MAX_SUBSTREAM_ID    = 0
