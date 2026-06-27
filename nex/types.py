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


def _write_key_value(out: StreamOut, key: str, value: str):
    # DataStoreKeyValue is a structure: header + Key(string) + Value(string)
    inner = StreamOut()
    inner.string(key)
    inner.string(value)
    if USE_STRUCT_HEADER:
        out.u8(0)
        out.u32(len(inner.get()))
    out.write(inner.get())


def write_req_post_info(out: StreamOut, data_id: int, url: str, form_fields: list):
    # DataStoreReqPostInfo.WriteTo:
    #   DataID(u64) + URL(string) + RequestHeaders(List<KV>) +
    #   FormFields(List<KV>) + RootCACert(Buffer)
    # form_fields is a list of (key, value) tuples.
    def body(s: StreamOut):
        s.u64(data_id)
        s.string(url)
        s.u32(0)                       # RequestHeaders: empty list
        s.u32(len(form_fields))        # FormFields: list count
        for k, v in form_fields:
            _write_key_value(s, k, v)
        s.u32(0)                       # RootCACert: buffer length 0

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


def write_permission(out: StreamOut, permission: int = 0):
    # DataStorePermission is a structure: header + Permission(u8) + RecipientIDs(List<PID>)
    inner = StreamOut()
    inner.u8(permission)
    inner.u32(0)              # empty RecipientIDs list
    if USE_STRUCT_HEADER:
        out.u8(0)
        out.u32(len(inner.get()))
    out.write(inner.get())


def write_meta_info(out: StreamOut, row: dict, owner_id: int):
    # Exact match of DataStoreMetaInfo.WriteTo + the Go freePlayDataToDataStoreMetaInfo mapping.
    EXPIRE_TIME_9999 = 671075926016   # December 31st, year 9999

    def body(s: StreamOut):
        s.u64(row['data_id'])
        s.pid(owner_id)
        s.u32(0)                              # Size = 0 (matches Go)
        s.string("FreePlayData")              # Name
        s.u16(row.get('data_type', 100))      # DataType (100 = Free Play Data)
        s.qbuffer(row['meta_binary'])         # MetaBinary
        write_permission(s, 0)                # Permission (0)
        write_permission(s, 3)                # DelPermission (3)
        s.datetime(row['created_time'])
        s.datetime(row['updated_time'])
        s.u16(row['period'])
        s.u8(0)                               # Status
        s.u32(0)                              # ReferredCnt
        s.u32(0)                              # ReferDataID
        s.u32(row['flag'])                    # Flag (u32 — the 3DS expects 4 bytes here)
        s.datetime(row['referred_time'])
        s.datetime(EXPIRE_TIME_9999)          # ExpireTime
        s.u32(0)                              # Tags: empty list
        s.u32(0)                              # Ratings: empty list

    write_struct(out, 1, body)
