import struct
from dataclasses import dataclass, field

MAGIC = b'\xEA\xD0'

TYPE_SYN        = 0
TYPE_CONNECT    = 1
TYPE_DATA       = 2
TYPE_DISCONNECT = 3
TYPE_PING       = 4

FLAG_ACK       = 0x001
FLAG_RELIABLE  = 0x002
FLAG_NEED_ACK  = 0x004
FLAG_HAS_SIZE  = 0x008
FLAG_MULTI_ACK = 0x200

OPT_SUPPORT    = 0
OPT_CONN_SIG   = 1
OPT_FRAGMENT   = 2
OPT_INIT_UNRELIABLE = 3
OPT_MAX_SUBSTREAM   = 4

@dataclass
class Packet:
    ptype:       int   = 0
    flags:       int   = 0
    session_id:  int   = 0
    substream_id: int  = 0
    seq_id:      int   = 0
    src:         int   = 0
    dst:         int   = 0
    fragment_id: int   = 0
    conn_sig:    bytes = field(default_factory=lambda: bytes(16))
    minor_version: int = 0
    supported_functions: int = 0
    max_substream_id: int = 0
    init_unreliable_seq: int = 0
    signature:   bytes = field(default_factory=lambda: bytes(16))
    payload:     bytes = b''

    def has_flag(self, f: int) -> bool:
        return bool(self.flags & f)

def decode(data: bytes) -> list:
    packets = []
    offset  = 0
    while offset < len(data):
        if data[offset:offset+2] != MAGIC:
            raise ValueError(f"Bad PRUDP V1 magic at offset {offset}")
        offset += 2

        if offset + 12 > len(data):
            raise ValueError("Truncated header")

        version     = data[offset];     offset += 1
        opts_len    = data[offset];     offset += 1
        payload_len = struct.unpack_from('<H', data, offset)[0]; offset += 2
        src         = data[offset];     offset += 1
        dst         = data[offset];     offset += 1
        type_flags  = struct.unpack_from('<H', data, offset)[0]; offset += 2
        session_id  = data[offset];     offset += 1
        substream_id = data[offset];    offset += 1
        seq_id      = struct.unpack_from('<H', data, offset)[0]; offset += 2

        if version != 1:
            raise ValueError(f"Expected PRUDPv1, got version {version}")

        if offset + 16 > len(data):
            raise ValueError("Truncated signature")
        signature = data[offset:offset+16]; offset += 16

        opts_data = data[offset:offset+opts_len]; offset += opts_len
        payload   = data[offset:offset+payload_len]; offset += payload_len

        pkt = Packet(
            ptype        = type_flags & 0xF,
            flags        = type_flags >> 4,
            session_id   = session_id,
            substream_id = substream_id,
            seq_id       = seq_id,
            src          = src,
            dst          = dst,
            signature    = signature,
            payload      = payload,
        )
        _decode_options(pkt, opts_data)
        packets.append(pkt)
    return packets

def _decode_options(pkt: Packet, data: bytes):
    pos = 0
    while pos < len(data):
        opt_id   = data[pos];   pos += 1
        opt_size = data[pos];   pos += 1
        val      = data[pos:pos+opt_size]; pos += opt_size

        if pkt.ptype in (TYPE_SYN, TYPE_CONNECT):
            if opt_id == OPT_SUPPORT and len(val) == 4:
                v = struct.unpack_from('<I', val)[0]
                pkt.minor_version        = v & 0xFF
                pkt.supported_functions  = v >> 8
            elif opt_id == OPT_CONN_SIG and len(val) == 16:
                pkt.conn_sig = val
            elif opt_id == OPT_MAX_SUBSTREAM and len(val) == 1:
                pkt.max_substream_id = val[0]
        if pkt.ptype == TYPE_CONNECT:
            if opt_id == OPT_INIT_UNRELIABLE and len(val) == 2:
                pkt.init_unreliable_seq = struct.unpack_from('<H', val)[0]
        if pkt.ptype == TYPE_DATA:
            if opt_id == OPT_FRAGMENT and len(val) == 1:
                pkt.fragment_id = val[0]

def _encode_options(pkt: Packet) -> bytes:
    buf = bytearray()
    if pkt.ptype in (TYPE_SYN, TYPE_CONNECT):
        v = pkt.minor_version | (pkt.supported_functions << 8)
        buf += bytes([OPT_SUPPORT, 4]) + struct.pack('<I', v)
        buf += bytes([OPT_CONN_SIG, 16]) + pkt.conn_sig

        if pkt.ptype == TYPE_CONNECT:
            buf += bytes([OPT_INIT_UNRELIABLE, 2]) + struct.pack('<H', pkt.init_unreliable_seq)

        buf += bytes([OPT_MAX_SUBSTREAM, 1, pkt.max_substream_id])
    if pkt.ptype == TYPE_DATA:
        buf += bytes([OPT_FRAGMENT, 1, pkt.fragment_id])
    return bytes(buf)

def _encode_header(pkt: Packet, opts_len: int, payload_len: int) -> bytes:
    type_flags = pkt.ptype | (pkt.flags << 4)
    return struct.pack('<BBHBBHBBH',
        1,
        opts_len,
        payload_len,
        pkt.src,
        pkt.dst,
        type_flags,
        pkt.session_id,
        pkt.substream_id,
        pkt.seq_id,
    )

def encode(pkt: Packet, access_key: str, session_key: bytes,
           conn_sig: bytes) -> bytes:
    from nex.crypto import packet_signature_v1

    options = _encode_options(pkt)
    header  = _encode_header(pkt, len(options), len(pkt.payload))

    pkt.signature = packet_signature_v1(
        access_key, header, session_key, conn_sig, options, pkt.payload
    )

    buf  = bytearray(MAGIC)
    buf += header
    buf += pkt.signature
    buf += options
    buf += pkt.payload
    return bytes(buf)

def make_ack(req: Packet) -> Packet:
    ack = Packet(
        ptype        = req.ptype,
        flags        = FLAG_ACK,
        src          = req.dst,
        dst          = req.src,
        session_id   = req.session_id,
        substream_id = req.substream_id,
        seq_id       = req.seq_id,
        conn_sig     = bytes(16),
    )
    return ack
