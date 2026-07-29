from nex.crypto import make_datetime_now
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
    out.u32(pid)
    out.string(public_url)
    return encode_success(PROTO_SECURE, method, call_id, out.get())

def _maintenance(call_id: int) -> bytes:
    out = StreamOut()
    out.u16(0xFFFF)
    out.u32(0)
    out.bool(True)
    return encode_success(PROTO_SECURE, M_MAINTENANCE, call_id, out.get())

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

def _skip_struct(inp: StreamIn):
    from nex.types import USE_STRUCT_HEADER
    if not USE_STRUCT_HEADER:
        return
    if inp.remaining() < 5:
        return
    _version = inp.u8()
    _length  = inp.u32()

class DataStorePreparePostParam:
    def __init__(self, inp: StreamIn):
        _skip_struct(inp)
        self.size        = inp.u32()
        self.name        = inp.string()
        self.data_type   = inp.u16()
        self.meta_binary = inp.qbuffer()

        _skip_struct(inp)
        inp.u8(); inp.list_pid()
        _skip_struct(inp)
        inp.u8(); inp.list_pid()

        self.flag   = inp.u32()
        self.period = inp.u16()

class DataStorePrepareUpdateParam:
    def __init__(self, inp: StreamIn):
        _skip_struct(inp)
        self.data_id         = inp.u64()
        self.update_password = inp.u64()
        self.size            = inp.u32()
        self.modifies_flag   = inp.u32()

class DataStoreChangeMetaParam:
    def __init__(self, inp: StreamIn):
        _skip_struct(inp)
        self.data_id       = inp.u64()
        self.modifies_flag = inp.u32()
        self.name          = inp.string()

        _skip_struct(inp)
        inp.u8(); inp.list_pid()
        _skip_struct(inp)
        inp.u8(); inp.list_pid()

        self.period      = inp.u16()
        self.meta_binary = inp.qbuffer()

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
            return encode_error(PROTO_DS, method, call_id, 0x80690004)
        out = StreamOut()
        write_persistence_info(out, owner_id, slot, 0, data_id)
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_POST_META_BINARY:
        param = DataStorePreparePostParam(inp)
        log.info("[DS] PostMetaBinary pid=%d dtype=%d meta_bytes=%d", pid, param.data_type, len(param.meta_binary))

        if param.data_type == 100:
            slot = 0
            data_id = await _run(db.save_free_play_data, pid, slot, param.meta_binary, param.period, param.flag)

        out = StreamOut()
        out.u64(pid)
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_PREPARE_POST:
        param = DataStorePreparePostParam(inp)
        log.info("[DS] PreparePostObject pid=%d size=%d dtype=%d", pid, param.size, param.data_type)

        slot = 0
        data_id = await _run(db.get_data_id_for_owner_slot, pid, slot)
        if data_id is None:

            data_id = await _run(db.save_free_play_data, pid, slot, b"", param.period, param.flag)

        key = s3_store.data_key(data_id, 1)
        form_fields = [
            ("key", key),
            ("acl", "private"),
            ("signature", "signature"),
        ]
        upload_url = s3_store.object_url("")
        log.info("[DS] PreparePostObject -> upload_url=%s key=%s", upload_url, key)
        out = StreamOut()
        write_req_post_info(out, data_id, upload_url, form_fields)
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_COMPLETE_POST:
        _skip_struct(inp)
        data_id    = inp.u64()
        is_success = inp.bool()
        log.info("[DS] CompletePostObject pid=%d data_id=%d ok=%s", pid, data_id, is_success)
        if not is_success:
            return encode_error(PROTO_DS, method, call_id, 0x80380104)
        await _run(db.update_play_info_version, data_id, 1)
        return encode_success(PROTO_DS, method, call_id, b"")

    elif method == M_PREPARE_GET:
        _skip_struct(inp)
        data_id = inp.u64()
        log.info("[DS] PrepareGetObject pid=%d data_id=%d", pid, data_id)
        version = await _run(db.get_version_by_data_id, data_id)
        if version == 0:
            version = 1
        key  = s3_store.data_key(data_id, version)
        size = s3_store.object_size(key)
        if size == 0:
            log.warning("[DS] PrepareGetObject: no save file on disk for %s", key)
        dl_url = s3_store.object_url(key)
        log.info("[DS] PrepareGetObject -> download_url=%s size=%d", dl_url, size)
        out  = StreamOut()
        write_req_get_info(out, dl_url, size, data_id)
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_GET_META_BY_OWNER:
        _skip_struct(inp)
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
        out.bool(False)
        return encode_success(PROTO_DS, method, call_id, out.get())

    elif method == M_CHANGE_META:
        param = DataStoreChangeMetaParam(inp)
        log.info("[DS] ChangeMeta pid=%d data_id=%d flags=0x%X",
                  pid, param.data_id, param.modifies_flag)

        if param.modifies_flag & (0x08 | 0x10):
            await _run(db.update_free_play_meta_binary, param.data_id, param.meta_binary, make_datetime_now())
        return encode_success(PROTO_DS, method, call_id, b"")

    elif method == M_PREPARE_UPDATE:
        param = DataStorePrepareUpdateParam(inp)
        log.info("[DS] PrepareUpdateObject pid=%d data_id=%d size=%d", pid, param.data_id, param.size)
        version     = await _run(db.get_version_by_data_id, param.data_id)
        new_version = version + 1
        key         = s3_store.data_key(param.data_id, new_version)
        form_fields = [
            ("key", key),
            ("acl", "private"),
            ("signature", "signature"),
        ]
        upload_url  = s3_store.object_url("")
        log.info("[DS] PrepareUpdateObject -> upload_url=%s key=%s newver=%d", upload_url, key, new_version)
        out         = StreamOut()
        write_req_update_info(out, new_version, upload_url, form_fields)
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

PROTO_SHOP         = 0xC8
M_GET_RIV_TOKEN    = 0x1
M_POST_PLAY_LOG    = 0x2

async def handle_shop(method: int, call_id: int,
                       params: bytes, pid: int) -> bytes:
    inp = StreamIn(params)
    if method == M_GET_RIV_TOKEN:
        item_code = inp.string()
        try:
            reference_id = inp.qbuffer()
        except Exception:
            reference_id = b""
        log.info("[Shop] GetRivToken pid=%d item=%r ref=%d bytes", pid, item_code, len(reference_id))
        out = StreamOut(); out.string("dummytoken")
        return encode_success(PROTO_SHOP, method, call_id, out.get())

    elif method == M_POST_PLAY_LOG:
        log.info("[Shop] PostPlayLog pid=%d", pid)
        return encode_success(PROTO_SHOP, method, call_id, b"")

    else:
        log.warning("[Shop] Unknown method 0x%X pid=%d", method, pid)
        return encode_error(PROTO_SHOP, method, call_id, 0x80010002)
