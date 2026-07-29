import logging
import secrets

from nex.stream  import StreamIn, StreamOut
from nex.crypto  import (derive_kerberos_key, build_server_ticket,
                          build_client_ticket, make_datetime_now)
from nex.rmc     import encode_success, encode_error, SUCCESS
from nex.types   import write_rv_connection_data
import config
import db

log = logging.getLogger(__name__)

PROTOCOL_ID       = 0xA
METHOD_LOGIN      = 1
METHOD_LOGIN_EX   = 2
METHOD_REQ_TICKET = 3

SERVER_PID        = 2

def _server_key():
    return derive_kerberos_key(SERVER_PID, config.kerberos_password().encode())

def _make_ticket(user_pid: int, user_password: str) -> bytes:
    session_key  = secrets.token_bytes(config.KERBEROS_KEY_SIZE)
    srv_ticket   = build_server_ticket(session_key, user_pid, _server_key())
    user_key     = derive_kerberos_key(user_pid, user_password.encode())
    return build_client_ticket(session_key, SERVER_PID, srv_ticket, user_key)

def _login_response(method: int, call_id: int, account: dict) -> bytes:
    pid      = account['pid']
    password = account['password']
    ticket   = _make_ticket(pid, password)

    location = config.secure_server_location()
    port     = config.secure_server_port()
    url      = (f"prudps:/address={location};port={port};"
                f"CID=1;PID={SERVER_PID};sid=1;stream=10;type=2")

    out = StreamOut()
    out.result(SUCCESS)
    out.pid(pid)
    out.buffer(ticket)
    write_rv_connection_data(out, url, make_datetime_now())
    out.string("Badge Arcade Auth")

    log.info("[Auth] Ticket issued pid=%d", pid)
    return encode_success(PROTOCOL_ID, method, call_id, out.get())

def _error_response(call_id: int, method: int) -> bytes:
    return encode_error(PROTOCOL_ID, method, call_id, 0x80150001)

async def handle(method: int, call_id: int, params: bytes) -> bytes:
    inp = StreamIn(params)

    if method in (METHOD_LOGIN, METHOD_LOGIN_EX):
        username = inp.string()
        log.info("[Auth] Login%s username=%r", "Ex" if method == METHOD_LOGIN_EX else "", username)

        import anyio
        account = await anyio.to_thread.run_sync(
            lambda: db.get_or_create_nex_account(username)
        )
        if account is None:
            log.warning("[Auth] Unknown username=%r", username)
            return _error_response(call_id, method)
        return _login_response(method, call_id, account)

    elif method == METHOD_REQ_TICKET:
        source = inp.pid()
        target = inp.pid()
        log.info("[Auth] RequestTicket source=%d target=%d", source, target)

        import anyio
        account = await anyio.to_thread.run_sync(
            lambda: db.get_nex_account_by_pid(source)
        )
        if account is None:

            account = await anyio.to_thread.run_sync(
                lambda: db.create_nex_account(source, str(source))
            )

        ticket = _make_ticket(source, account['password'])
        out    = StreamOut()
        out.result(SUCCESS)
        out.buffer(ticket)
        return encode_success(PROTOCOL_ID, method, call_id, out.get())

    else:
        log.warning("[Auth] Unknown method 0x%X", method)
        return encode_error(PROTOCOL_ID, method, call_id, 0x80010002)
