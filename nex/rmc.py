import struct

SUCCESS   = 0x00010001
ERROR_MASK = 0x80000000

class RMCRequest:
    def __init__(self, protocol: int, method: int, call_id: int, params: bytes):
        self.protocol = protocol
        self.method   = method
        self.call_id  = call_id
        self.params   = params

def decode_request(data: bytes) -> RMCRequest:
    if len(data) < 4:
        raise ValueError("RMC too short")
    length = struct.unpack_from('<I', data)[0]
    body   = data[4:]
    if len(body) != length:
        raise ValueError(f"RMC length mismatch: want {length} have {len(body)}")

    pos        = 0
    proto_byte = body[pos]; pos += 1
    if proto_byte & 0x80 == 0:
        raise ValueError("RMC: not a request (high bit clear)")

    protocol = proto_byte & ~0x80
    if protocol == 0x7F:
        protocol = struct.unpack_from('<H', body, pos)[0]; pos += 2

    call_id = struct.unpack_from('<I', body, pos)[0]; pos += 4
    method  = struct.unpack_from('<I', body, pos)[0]; pos += 4
    params  = body[pos:]

    return RMCRequest(protocol, method, call_id, params)

def encode_success(protocol: int, method: int, call_id: int, params: bytes) -> bytes:
    buf = bytearray()
    if protocol < 0x80:
        buf.append(protocol)
    else:
        buf.append(0x7F)
        buf.extend(struct.pack('<H', protocol))
    buf.append(1)
    buf.extend(struct.pack('<I', call_id))
    buf.extend(struct.pack('<I', method | 0x8000))
    buf.extend(params)
    return _wrap(buf)

def encode_error(protocol: int, method: int, call_id: int, error_code: int) -> bytes:
    if not (error_code & ERROR_MASK):
        error_code |= ERROR_MASK
    buf = bytearray()
    if protocol < 0x80:
        buf.append(protocol)
    else:
        buf.append(0x7F)
        buf.extend(struct.pack('<H', protocol))
    buf.append(0)
    buf.extend(struct.pack('<I', error_code))
    buf.extend(struct.pack('<I', call_id))
    return _wrap(buf)

def _wrap(body: bytearray) -> bytes:
    return struct.pack('<I', len(body)) + bytes(body)
