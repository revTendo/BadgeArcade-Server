import struct

class StreamIn:
    def __init__(self, data: bytes):
        self._data = data
        self._pos  = 0

    def remaining(self) -> int:
        return len(self._data) - self._pos

    def eof(self) -> bool:
        return self._pos >= len(self._data)

    def read(self, n: int) -> bytes:
        if self._pos + n > len(self._data):
            raise ValueError(f"StreamIn: need {n} bytes, have {self.remaining()}")
        v = self._data[self._pos: self._pos + n]
        self._pos += n
        return v

    def read_remaining(self) -> bytes:
        return self.read(self.remaining())

    def u8(self)  -> int: return struct.unpack_from('<B', self.read(1))[0]
    def u16(self) -> int: return struct.unpack_from('<H', self.read(2))[0]
    def u32(self) -> int: return struct.unpack_from('<I', self.read(4))[0]
    def u64(self) -> int: return struct.unpack_from('<Q', self.read(8))[0]
    def bool(self) -> bool: return bool(self.u8())

    def pid(self) -> int:
        return self.u32()

    def string(self) -> str:
        length = self.u16()
        if length == 0:
            return ""
        raw = self.read(length)
        return raw.rstrip(b'\x00').decode('utf-8')

    def buffer(self) -> bytes:
        return self.read(self.u32())

    def qbuffer(self) -> bytes:
        return self.read(self.u16())

    def datetime(self) -> int:
        return self.u64()

    def list_u8(self)  -> list: return [self.u8()  for _ in range(self.u32())]
    def list_u16(self) -> list: return [self.u16() for _ in range(self.u32())]
    def list_u32(self) -> list: return [self.u32() for _ in range(self.u32())]
    def list_pid(self) -> list: return [self.pid() for _ in range(self.u32())]

    def result_range(self) -> tuple:
        return self.u32(), self.u32()

class StreamOut:
    def __init__(self):
        self._buf = bytearray()

    def get(self) -> bytes:
        return bytes(self._buf)

    def write(self, data: bytes):
        self._buf.extend(data)

    def u8(self, v: int):  self.write(struct.pack('<B', v & 0xFF))
    def u16(self, v: int): self.write(struct.pack('<H', v & 0xFFFF))
    def u32(self, v: int): self.write(struct.pack('<I', v & 0xFFFFFFFF))
    def u64(self, v: int): self.write(struct.pack('<Q', v & 0xFFFFFFFFFFFFFFFF))
    def bool(self, v: bool): self.u8(1 if v else 0)

    def pid(self, v: int): self.u32(v)

    def string(self, s: str):

        raw = (s + '\x00').encode('utf-8')
        self.u16(len(raw))
        self.write(raw)

    def buffer(self, data: bytes):
        self.u32(len(data))
        self.write(data)

    def qbuffer(self, data: bytes):
        self.u16(len(data))
        self.write(data)

    def datetime(self, v: int):
        self.u64(v)

    def list_u8(self, items: list):
        self.u32(len(items))
        for v in items: self.u8(v)

    def result(self, code: int = 0x00010001):
        self.u32(code)

    def struct_header(self, version: int, content: bytes):
        self.u8(version)
        self.u32(len(content))
        self.write(content)
