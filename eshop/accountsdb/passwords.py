import hashlib
import struct
import secrets
import string

_MAGIC = b"\x02\x65\x43\x46"

def nintendo_password_hash(password, pid):
    pid_int = int(str(pid).strip() or 0) & 0xFFFFFFFF
    unpacked = struct.pack("<I", pid_int) + _MAGIC + password.encode("utf-8")
    return hashlib.sha256(unpacked).hexdigest()

def make_stored_password(password, pid):
    import bcrypt
    primary = nintendo_password_hash(password, pid).encode("utf-8")
    return bcrypt.hashpw(primary, bcrypt.gensalt(rounds=10)).decode("utf-8")

def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in candidate)
                and any(c.isupper() for c in candidate)
                and any(c.isdigit() for c in candidate)):
            return candidate

def generate_email_code():
    return str(secrets.randbelow(900000) + 100000)
