import hashlib
import hmac
import secrets
import socket
import struct
import time

from Crypto.Cipher import ARC4


# ── Connection signature key (PRUDPv1) ────────────────────────────────────────
# Random 16-byte key generated once at startup, exactly like nex-go.
# Only the server ever verifies its own connection signature; the client
# simply echoes it back, so the actual value only needs to be consistent.
_CONN_SIG_KEY = secrets.token_bytes(16)


def connection_signature_v1(ip: str, port: int) -> bytes:
    data = socket.inet_aton(ip) + struct.pack(">H", port)
    return hmac.new(_CONN_SIG_KEY, data, hashlib.md5).digest()


# ── PRUDPv1 packet HMAC signature ─────────────────────────────────────────────
def packet_signature_v1(access_key: str, header12: bytes, session_key: bytes,
                         conn_sig: bytes, options: bytes, payload: bytes) -> bytes:
    ak  = access_key.encode()
    key = hashlib.md5(ak).digest()
    ak_sum = struct.pack('<I', sum(ak))

    mac = hmac.new(key, digestmod=hashlib.md5)
    mac.update(header12[4:])   # skip version(1)+optLen(1)+payloadLen(2)
    mac.update(session_key)
    mac.update(ak_sum)
    mac.update(conn_sig)
    mac.update(options)
    mac.update(payload)
    return mac.digest()


# ── Kerberos ──────────────────────────────────────────────────────────────────

def derive_kerberos_key(pid: int, password: bytes) -> bytes:
    count = 65000 + (pid % 1024)
    key = password
    for _ in range(count):
        key = hashlib.md5(key).digest()
    return key


def kerberos_encrypt(key: bytes, data: bytes) -> bytes:
    cipher = ARC4.new(key)
    enc    = cipher.encrypt(data)
    mac    = hmac.new(key, enc, hashlib.md5).digest()
    return enc + mac


def kerberos_decrypt(key: bytes, data: bytes) -> bytes:
    body, checksum = data[:-16], data[-16:]
    expected = hmac.new(key, body, hashlib.md5).digest()
    if not hmac.compare_digest(expected, checksum):
        raise ValueError("Kerberos: invalid HMAC (wrong password?)")
    cipher = ARC4.new(key)
    return cipher.decrypt(body)


def make_datetime_now() -> int:
    import datetime
    dt = datetime.datetime.now(datetime.timezone.utc)
    return (dt.second       |
            (dt.minute << 6)  |
            (dt.hour   << 12) |
            (dt.day    << 17) |
            (dt.month  << 22) |
            (dt.year   << 26))


def datetime_to_unix(dt_val: int) -> float:
    import datetime
    second = dt_val & 63
    minute = (dt_val >> 6)  & 63
    hour   = (dt_val >> 12) & 31
    day    = (dt_val >> 17) & 31
    month  = (dt_val >> 22) & 15
    year   =  dt_val >> 26
    try:
        d = datetime.datetime(year, month, day, hour, minute, second,
                              tzinfo=datetime.timezone.utc)
        return d.timestamp()
    except Exception:
        return 0.0


def build_server_ticket(session_key: bytes, source_pid: int, server_key: bytes) -> bytes:
    from nex.stream import StreamOut
    s = StreamOut()
    s.datetime(make_datetime_now())
    s.pid(source_pid)
    s.write(session_key)
    return kerberos_encrypt(server_key, s.get())


def build_client_ticket(session_key: bytes, target_pid: int,
                         server_ticket: bytes, user_key: bytes) -> bytes:
    from nex.stream import StreamOut
    s = StreamOut()
    s.write(session_key)
    s.pid(target_pid)
    s.buffer(server_ticket)
    return kerberos_encrypt(user_key, s.get())


def parse_server_ticket(data: bytes, server_key: bytes) -> tuple:
    from nex.stream import StreamIn
    raw = kerberos_decrypt(server_key, data)
    s   = StreamIn(raw)
    dt  = s.datetime()
    if time.time() - datetime_to_unix(dt) > 120:
        raise ValueError("Kerberos ticket expired")
    pid         = s.pid()
    session_key = s.read_remaining()
    return session_key, pid


# ── Stateful RC4 stream (maintained across packets) ───────────────────────────

class RC4Stream:
    def __init__(self, key: bytes):
        self._enc = ARC4.new(key)
        self._dec = ARC4.new(key)

    def encrypt(self, data: bytes) -> bytes:
        return self._enc.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        return self._dec.decrypt(data)
