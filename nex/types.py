import struct
from nex.stream import StreamOut


USE_STRUCT_HEADER = True   # NEX 30716 >= 30500, so structures DO get a header


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
    # Exact match of nex-go v1.0.12 RVConnectionData.Bytes() as used by the
    # original working Badge Arcade server. Because NEX 30716 >= 30500,
    # WriteStructure prepends a u8 version + u32 length header, then:
    #   WriteString(stationURL)
    #   WriteUInt32LE(0)                      // special protocols, always 0
    #   WriteString(stationURLSpecialProtocols)  // empty
    #   WriteUInt64LE(time)                   // ALWAYS written
    inner = StreamOut()
    write_station_url(inner, station_url)
    inner.u32(0)
    write_station_url(inner, "")
    inner.datetime(server_time)

    out.u8(1)                       # structure version (NEX >= 30500)
    out.u32(len(inner.get()))       # content length
    out.write(inner.get())


def write_persistence_info(out: StreamOut, owner_id: int, slot: int,
                            size: int, data_id: int):
    # Matches nex-protocols-go DataStorePersistenceInfo.WriteTo:
    #   OwnerID(u32) + PersistenceSlotID(u16) + DataID(u64)
    # (size is part of the newer struct but NOT serialized here)
    def body(s: StreamOut):
        s.pid(owner_id)
        s.u16(slot)
        s.u64(data_id)

    write_struct(out, 0, body)


def write_req_post_info(out: StreamOut, data_id: int, url: str, form: str):
    def body(s: StreamOut):
        s.u64(data_id)
        s.string(url)
        s.u32(0)          # empty headers list
        s.string(form)
        s.u32(0)          # root_ca_pem length = 0

    write_struct(out, 0, body)


def write_req_get_info(out: StreamOut, url: str, size: int, data_id: int = 0):
    # Matches DataStoreReqGetInfo.WriteTo:
    #   URL + RequestHeaders + Size + RootCACert + DataID
    def body(s: StreamOut):
        s.string(url)
        s.u32(0)          # empty RequestHeaders list
        s.u32(size)
        s.u32(0)          # RootCACert buffer, length 0
        s.u64(data_id)    # DataID (DataStore lib >= 3.5.0)

    write_struct(out, 0, body)


def write_req_update_info(out: StreamOut, version: int, url: str):
    def body(s: StreamOut):
        s.u32(version)
        s.string(url)
        s.u32(0)          # empty headers list
        s.string("")      # form
        s.u32(0)          # root_ca_pem length = 0

    write_struct(out, 0, body)


def write_permission(out: StreamOut):
    out.u8(0)    # permission_type
    out.u32(0)   # recipient_ids list (empty)


def write_meta_info(out: StreamOut, row: dict, owner_id: int):
    def body(s: StreamOut):
        s.u64(row['data_id'])
        s.pid(owner_id)
        s.u32(len(row['meta_binary']))
        s.string("")          # name
        s.u16(0)              # data_type
        s.qbuffer(row['meta_binary'])
        write_permission(s)   # permission
        write_permission(s)   # del_permission
        s.datetime(row['created_time'])
        s.datetime(row['updated_time'])
        s.u16(row['period'])
        s.u8(0)               # status
        s.u32(0)              # referred_cnt
        s.u32(0)              # refer_data_id
        s.u32(row['flag'])
        s.datetime(row['referred_time'])
        s.datetime(0)         # expire_time
        s.u32(0)              # tags (empty)
        s.u32(0)              # ratings (empty)

    write_struct(out, 1, body)
