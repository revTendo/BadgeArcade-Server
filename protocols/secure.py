import logging
import time

from nex.stream import StreamIn, StreamOut
from nex.rmc    import encode_success, encode_error, SUCCESS
from nex.types  import (write_persistence_info, write_req_post_info,
                         write_req_get_info, write_req_update_info,
                         write_meta_info)
import db
import s3_store

log = logging.getLogger(__name__)

import anyio


async def _run(fn, *args):
    return await anyio.to_thread.run_sync(lambda: fn(*args))


# ── SecureConnection (0x0B) ───────────────────────────────────────────────────

PROTO_SECURE    = 0x0B
M_REGISTER      = 0x1
M_REGISTER_EX   = 0x4
M_MAINTENANCE   = 0x9


async def handle_secure(method: int, call_id: int, params: bytes,
                         pid: int, client_addr: tuple) -> bytes:
    if method in (M_REGISTER, M_REGISTER_EX):
        return await _register(method, call_id, params, pid, client_addr)
    elif method == M_MAINTENANCE:
        return _maintenance(call_id)
    else:
        log.warning("[Secure] Unknown method 0x%X", method)
        return encode_error(PROTO_SECURE, method, call_id, 0x80010002)


async def _register(method: int, call_id: int, params: bytes,
                     pid: int, client_addr: tuple) -> bytes:
    inp      = StreamIn(params)
    url_count = inp.u32()
    urls = []
    for _ in range(url_count):
        urls.append(inp.string())

    addr, port = client_addr
    log.info("[Secure] Register pid=%d urls=%d from %s:%d", pid, len(urls), addr, port)

    public_url = ""
    for u in urls:
        if "type=2" in u or "type=3" in u:
            public_url = u
            break
    if not public_url and urls:
        public_url = urls[0]

    if ";address=" in public_url:
        parts = {}
        scheme, rest = public_url.split(":/", 1)
        for kv in rest.split(";"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                parts[k] = v
        parts["address"] = addr
        parts["port"]    = str(port)
        public_url = scheme + ":/" + ";".join(f"{k}={v}" for k, v in parts.items())
    else:
        public_url = f"prudp:/address={addr};port={port};stream=10;sid=1;type=2"

    exists = await _run(db.session_exists, pid)
    fn     = db.update_session if exists else db.add_session
    await _run(fn, pid, urls, addr, str(port))

    out = StreamOut()
    out.result(SUCCESS)
    out.u32(pid)          # connection ID = PID
    out.string(public_url)
    return encode_success(PROTO_SECURE, method, call_id, out.get())


def _maintenance(call_id: int) -> bytes:
    out = StreamOut()
    out.u16(0x0000)
    out.u32(0)
    out.bool(True)
    return encode_success(PROTO_SECURE, M_MAINTENANCE, call_id, out.get())


# ── DataStore (0x73) ──────────────────────────────────────────────────────────

PROTO_DS            = 0x73
M_PREPARE_GET       = 25
M_PREPARE_POST      = 24
M_COMPLETE_POST     = 26
M_PREPARE_UPDATE    = 10
M_COMPLETE_UPDATE   = 11
M_POST_META_BINARY  = 21
M_GET_PERSISTENCE   = 29
M_CHANGE_META       = 38
M_GET_META_BY_OWNER = 0x2D


async def handle_datastore(method: int, call_id: int,
                            params: bytes, pid: int) -> bytes:
    try:
        return await _ds_dispatch(method, call_id, params, pid)
    except Exception:
        log.exception("[DS] method=0x%X pid=%d", method, pid)
        return encode_error(PROTO_DS, method, call_id, 0x80010002)


async def _ds_dispatch(method, call_id, params, pid):
    inp = StreamIn(params)

    if method == M_GET_PERSISTENCE:
        owner_id = inp.pid()
        slot     = inp.u16()
        log.info("[DS] GetPersistenceInfo pid=%d owner=%d slot=%d", pid, owner_id, slot)
        data_id  = await _run(db.get_persistence_info, owner_id, slot)
        if data_id == 0:
            # No data for this owner/slot → DataStore::NotFound (matches Go server)
            return encode_error(PROTO_DS, method, call_id, 0x80690004)
        out = StreamOut()
        write_persistence_info(out, owner_id, slot, 0, data_id)
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_POST_META_BINARY:
        # Skip PreparePostParam structure header if present
        _skip_struct(inp)
        slot        = inp.u16() if inp.remaining() >= 2 else 0
        period      = inp.u16() if inp.remaining() >= 2 else 0
        meta_binary = inp.qbuffer() if inp.remaining() > 2 else b""
        flag        = inp.u32() if inp.remaining() >= 4 else 0
        now         = int(time.time())
        data_id     = (now * 1000) & 0xFFFFFFFF
        log.info("[DS] PostMetaBinary pid=%d slot=%d", pid, slot)
        await _run(db.insert_free_play_data, data_id, pid, meta_binary, now, period, flag)
        await _run(db.insert_user_play_info, data_id, pid, slot)
        out = StreamOut(); out.u64(data_id)
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_PREPARE_POST:
        _skip_struct(inp)
        size    = inp.u32() if inp.remaining() >= 4 else 0
        slot    = inp.u16() if inp.remaining() >= 2 else 0
        period  = inp.u16() if inp.remaining() >= 2 else 0
        flag    = inp.u32() if inp.remaining() >= 4 else 0
        now     = int(time.time())
        data_id = (now * 1000) & 0xFFFFFFFF
        log.info("[DS] PreparePostObject pid=%d size=%d", pid, size)
        await _run(db.insert_free_play_data, data_id, pid, b"", now, period, flag)
        await _run(db.insert_user_play_info, data_id, pid, slot)
        key = s3_store.data_key(data_id, 0)
        out = StreamOut()
        write_req_post_info(out, data_id, s3_store.object_url(key),
                             "x-amz-acl=public-read&Content-Type=application/octet-stream")
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_COMPLETE_POST:
        _skip_struct(inp)
        data_id    = inp.u64()
        is_success = inp.bool()
        log.info("[DS] CompletePostObject pid=%d data_id=%d ok=%s", pid, data_id, is_success)
        if not is_success:
            return encode_error(PROTO_DS, method, call_id, 0x80380104)
        return encode_success(PROTO_DS, method, call_id, b"")

    elif method == M_PREPARE_GET:
        _skip_struct(inp)
        data_id = inp.u64()
        log.info("[DS] PrepareGetObject pid=%d data_id=%d", pid, data_id)
        version = await _run(db.get_version_by_data_id, data_id)
        key     = s3_store.data_key(data_id, version)
        size    = s3_store.object_size(key)
        out     = StreamOut()
        write_req_get_info(out, s3_store.object_url(key), size, data_id)
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_GET_META_BY_OWNER:
        owner_ids    = inp.list_pid()
        _data_types  = inp.list_u16()
        _result_opt  = inp.u8()
        _offset, _sz = inp.result_range()
        log.info("[DS] GetMetaByOwnerID pid=%d owners=%s", pid, owner_ids)
        results = []
        for oid in owner_ids:
            row = await _run(db.get_free_play_data_by_owner, oid)
            if row:
                results.append((oid, row))
        out = StreamOut()
        out.u32(len(results))
        for oid, row in results:
            write_meta_info(out, row, oid)
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_CHANGE_META:
        _skip_struct(inp)
        data_id       = inp.u64()
        modifies_flag = inp.u32()
        log.info("[DS] ChangeMeta pid=%d data_id=%d flags=0x%X",
                  pid, data_id, modifies_flag)
        if modifies_flag & 0x08:
            meta_binary = inp.qbuffer()
            await _run(db.update_free_play_meta_binary, data_id, meta_binary, int(time.time()))
        return encode_success(PROTO_DS, method, call_id, b"")

    elif method == M_PREPARE_UPDATE:
        _skip_struct(inp)
        data_id = inp.u64()
        size    = inp.u32()
        log.info("[DS] PrepareUpdateObject pid=%d data_id=%d size=%d", pid, data_id, size)
        version     = await _run(db.get_version_by_data_id, data_id)
        new_version = version + 1
        key         = s3_store.data_key(data_id, new_version)
        out         = StreamOut()
        write_req_update_info(out, new_version, s3_store.object_url(key))
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_COMPLETE_UPDATE:
        _skip_struct(inp)
        data_id    = inp.u64()
        version    = inp.u32()
        is_success = inp.bool()
        log.info("[DS] CompleteUpdateObject pid=%d data_id=%d v=%d ok=%s",
                  pid, data_id, version, is_success)
        if not is_success:
            return encode_error(PROTO_DS, method, call_id, 0x80380104)
        await _run(db.update_play_info_version, data_id, version)
        return encode_success(PROTO_DS, method, call_id, b"")

    else:
        log.warning("[DS] Unknown method 0x%X pid=%d", method, pid)
        return encode_error(PROTO_DS, method, call_id, 0x80010002)


def _skip_struct(inp: StreamIn):
    # 3DS Badge Arcade does NOT use structure headers, so there is nothing
    # to skip. Kept as a no-op so call sites stay readable.
    return


# ── Shop Badge Arcade (0xC8) ──────────────────────────────────────────────────

PROTO_SHOP         = 0xC8
M_GET_RIV_TOKEN    = 0x1
M_POST_PLAY_LOG    = 0x2


async def handle_shop(method: int, call_id: int,
                       params: bytes, pid: int) -> bytes:
    inp = StreamIn(params)
    if method == M_GET_RIV_TOKEN:
        item_code = inp.string()
        log.info("[Shop] GetRivToken pid=%d item=%r", pid, item_code)
        out = StreamOut(); out.string("")
        return encode_success(PROTO_SHOP, method, call_id, out.get())

    elif method == M_POST_PLAY_LOG:
        log.info("[Shop] PostPlayLog pid=%d", pid)
        return encode_success(PROTO_SHOP, method, call_id, b"")

    else:
        log.warning("[Shop] Unknown method 0x%X pid=%d", method, pid)
        return encode_error(PROTO_SHOP, method, call_id, 0x80010002)
