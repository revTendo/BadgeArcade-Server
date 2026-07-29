import struct
from nex.stream import StreamOut

USE_STRUCT_HEADER = True

def write_struct(out: StreamOut, version: int, write_fn):
    if USE_STRUCT_HEADER:
        inner = StreamOut()
        write_fn(inner)
        out.u8(version)
        out.u32(len(inner.get()))
        out.write(inner.get())
    else:
        write_fn(out)

def write_station_url(out: StreamOut, url: str):
    out.string(url)

def write_rv_connection_data(out: StreamOut, station_url: str, server_time: int):

    inner = StreamOut()
    write_station_url(inner, station_url)
    inner.u32(0)
    write_station_url(inner, "")
    inner.datetime(server_time)

    out.u8(1)
    out.u32(len(inner.get()))
    out.write(inner.get())

def write_persistence_info(out: StreamOut, owner_id: int, slot: int,
                            size: int, data_id: int):

    def body(s: StreamOut):
        s.pid(owner_id)
        s.u16(slot)
        s.u64(data_id)

    write_struct(out, 0, body)

def _write_key_value(out: StreamOut, key: str, value: str):

    inner = StreamOut()
    inner.string(key)
    inner.string(value)
    if USE_STRUCT_HEADER:
        out.u8(0)
        out.u32(len(inner.get()))
    out.write(inner.get())

def write_req_post_info(out: StreamOut, data_id: int, url: str, form_fields: list):

    def body(s: StreamOut):
        s.u64(data_id)
        s.string(url)
        s.u32(0)
        s.u32(len(form_fields))
        for k, v in form_fields:
            _write_key_value(s, k, v)
        s.u32(0)

    write_struct(out, 0, body)

def write_req_get_info(out: StreamOut, url: str, size: int, data_id: int = 0):

    def body(s: StreamOut):
        s.string(url)
        s.u32(0)
        s.u32(size)
        s.u32(0)
        s.u64(data_id)

    write_struct(out, 0, body)

def write_req_update_info(out: StreamOut, version: int, url: str, form_fields: list = None):

    form_fields = form_fields or []
    def body(s: StreamOut):
        s.u32(version)
        s.string(url)
        s.u32(0)
        s.u32(len(form_fields))
        for k, v in form_fields:
            _write_key_value(s, k, v)
        s.u32(0)

    write_struct(out, 0, body)

def write_permission(out: StreamOut, permission: int = 0):

    inner = StreamOut()
    inner.u8(permission)
    inner.u32(0)
    if USE_STRUCT_HEADER:
        out.u8(0)
        out.u32(len(inner.get()))
    out.write(inner.get())

def write_meta_info(out: StreamOut, row: dict, owner_id: int):

    EXPIRE_TIME_9999 = 671075926016

    def body(s: StreamOut):
        s.u64(row['data_id'])
        s.pid(owner_id)
        s.u32(0)
        s.string("FreePlayData")
        s.u16(row.get('data_type', 100))
        s.qbuffer(row['meta_binary'])
        write_permission(s, 0)
        write_permission(s, 3)
        s.datetime(row['created_time'])
        s.datetime(row['updated_time'])
        s.u16(row['period'])
        s.u8(0)
        s.u32(0)
        s.u32(0)
        s.u32(row['flag'])
        s.datetime(row['referred_time'])
        s.datetime(EXPIRE_TIME_9999)
        s.u32(0)
        s.u32(0)

    write_struct(out, 1, body)
