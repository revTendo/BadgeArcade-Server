import asyncio
import logging
import secrets
import struct
import time

from nex import packet as pkt
from nex.crypto import (connection_signature_v1, kerberos_decrypt,
                         parse_server_ticket, RC4Stream)
from nex import rmc as rmc_mod
import config

log = logging.getLogger(__name__)

PING_INTERVAL = 5.0

CONNECTION_IDLE_TIMEOUT = 300.0
CD_ML         = b'CD&ML'

TYPE_NAMES = ['SYN','CONNECT','DATA','DISCONNECT','PING','USER','ROUTE','RAW']
pkt.TYPE_NAMES = TYPE_NAMES

class Connection:
    STATE_INIT      = 0
    STATE_CONNECTED = 1

    def __init__(self, addr):
        self.addr            = addr
        self.session_id      = secrets.randbits(8)
        self.data_seq        = 1
        self.ping_seq        = 1
        self.pid             = 0
        self.session_key     = b''
        self.rc4             = None
        self.pending         = {}
        self.seen_data_seqs  = set()
        self.last_ack        = time.monotonic()
        self.client_conn_sig = bytes(16)
        self.client_vport    = 0xA1
        self.server_vport    = 0x11
        self.state           = self.STATE_INIT
        self.minor_version   = 0

class PRUDPServer:
    def __init__(self, port, mode, dispatch_fn, server_key=None):
        self.port       = port
        self.mode       = mode
        self.dispatch   = dispatch_fn
        self.server_key = server_key
        self.conns      = {}
        self.transport  = None

    async def start(self):
        loop = asyncio.get_event_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: _Protocol(self),
            local_addr=('0.0.0.0', self.port)
        )
        log.info("[%s] listening on 0.0.0.0:%d", self.mode, self.port)

    def stop(self):
        if self.transport:
            self.transport.close()

    def _raw_send(self, conn, p):
        raw = pkt.encode(p, config.ACCESS_KEY, conn.session_key, conn.client_conn_sig)
        self.transport.sendto(raw, conn.addr)
        log.debug("[%s] SND %s seq=%d", self.mode, TYPE_NAMES[p.ptype], p.seq_id)

    def _ack(self, conn, req):
        a              = pkt.make_ack(req)
        a.session_id   = conn.session_id
        a.src          = conn.server_vport
        a.dst          = conn.client_vport
        self._raw_send(conn, a)

    def process(self, data, addr):
        try:
            packets = pkt.decode(data)
        except Exception as e:
            log.warning("[%s] decode error from %s: %s", self.mode, addr, e)
            return
        for p in packets:
            self._route(p, addr)

    def _route(self, p, addr):
        conn = self.conns.get(addr)

        if conn is None and p.ptype not in (pkt.TYPE_SYN, pkt.TYPE_CONNECT):
            sid = getattr(p, "session_id", 0)
            if sid:
                for old_addr, c in list(self.conns.items()):
                    if c.session_id == sid and old_addr[0] == addr[0]:

                        log.info("[%s] session %d moved %s -> %s (NAT remap)",
                                 self.mode, sid, old_addr, addr)
                        self.conns.pop(old_addr, None)
                        c.addr = addr
                        self.conns[addr] = c
                        conn = c
                        break

        if conn is not None:
            conn.last_ack = time.monotonic()

        if p.has_flag(pkt.FLAG_MULTI_ACK):
            if conn:
                conn.last_ack = time.monotonic()
                self._handle_aggregate_ack(p, conn)
            return

        if p.has_flag(pkt.FLAG_ACK):
            if conn:
                conn.last_ack = time.monotonic()

                conn.pending.pop((p.ptype, p.seq_id), None)
            return

        log.debug("[%s] RCV %s seq=%d from %s", self.mode, TYPE_NAMES[p.ptype], p.seq_id, addr)

        if p.ptype == pkt.TYPE_SYN:
            self._syn(p, addr)
        elif p.ptype == pkt.TYPE_CONNECT:
            if conn is None:
                conn = Connection(addr)
                self.conns[addr] = conn
            self._connect(p, addr, conn)
        elif p.ptype == pkt.TYPE_DATA and conn and conn.state == Connection.STATE_CONNECTED:
            self._data(p, addr, conn)
        elif p.ptype == pkt.TYPE_PING and conn:
            conn.last_ack = time.monotonic()
            self._ack(conn, p)
        elif p.ptype == pkt.TYPE_DISCONNECT and conn:
            if p.has_flag(pkt.FLAG_NEED_ACK):
                self._ack(conn, p)
            self.conns.pop(addr, None)
            log.info("[%s] DISCONNECT pid=%d", self.mode, conn.pid)

    def _handle_aggregate_ack(self, p, conn):

        payload = p.payload
        try:
            if p.substream_id == 1 and len(payload) >= 4:
                count   = payload[1]
                base_id = struct.unpack_from('<H', payload, 2)[0]
                extra   = struct.unpack_from('<%iH' % count, payload, 4) if count else ()
            else:
                base_id = p.seq_id
                extra   = struct.unpack('<%iH' % (len(payload) // 2), payload) if payload else ()
        except Exception:
            base_id, extra = p.seq_id, ()

        for key in list(conn.pending):
            ktype, kseq = key
            if ktype == pkt.TYPE_DATA and (kseq <= base_id or kseq in extra):
                conn.pending.pop(key, None)

    def _syn(self, p, addr):

        old = self.conns.pop(addr, None)
        if old is not None:
            old.pending.clear()
            log.debug("[%s] SYN replacing existing connection from %s", self.mode, addr)

        conn = Connection(addr)
        conn.client_vport    = p.src
        conn.server_vport    = p.dst
        conn.server_conn_sig = connection_signature_v1(addr[0], addr[1])
        conn.minor_version   = min(config.PRUDP_MINOR_VERSION, p.minor_version)
        self.conns[addr]     = conn

        ack                     = pkt.Packet(ptype=pkt.TYPE_SYN,
                                             flags=pkt.FLAG_ACK | pkt.FLAG_HAS_SIZE)
        ack.src                 = conn.server_vport
        ack.dst                 = conn.client_vport
        ack.session_id          = 0
        ack.conn_sig            = conn.server_conn_sig

        ack.minor_version       = conn.minor_version
        ack.supported_functions = config.PRUDP_SUPPORTED_FUNCTIONS & p.supported_functions
        ack.max_substream_id    = min(config.PRUDP_MAX_SUBSTREAM_ID, p.max_substream_id)

        raw = pkt.encode(ack, config.ACCESS_KEY, b'', b'')
        self.transport.sendto(raw, addr)
        log.debug("[%s] SYN-ACK → %s minor=%d funcs=%d max_sub=%d",
                  self.mode, addr, conn.minor_version,
                  ack.supported_functions, ack.max_substream_id)

    def _connect(self, p, addr, conn):
        conn.client_conn_sig = p.conn_sig
        conn.client_vport    = p.src
        conn.server_vport    = p.dst

        log.debug("[%s] CONNECT recv: payload=%d bytes client_sig=%s minor=%d",
                  self.mode, len(p.payload), p.conn_sig.hex()[:12], p.minor_version)

        ack_payload = b''

        if self.server_key is None:

            conn.rc4 = RC4Stream(CD_ML)
            conn.state = Connection.STATE_CONNECTED
            log.info("[%s] CONNECT from %s", self.mode, addr)

        else:

            if not p.payload:
                log.error("[%s] CONNECT from %s: empty payload", self.mode, addr)
                self.conns.pop(addr, None)
                return
            try:
                from nex.stream import StreamIn
                s            = StreamIn(p.payload)
                ticket_data  = s.buffer()
                request_data = s.buffer()

                session_key, source_pid = parse_server_ticket(ticket_data, self.server_key)

                decrypted = kerberos_decrypt(session_key, request_data)
                rs        = StreamIn(decrypted)
                req_pid   = rs.pid()
                _         = rs.u32()
                check_val = rs.u32()

                if req_pid != source_pid:
                    raise ValueError(f"PID mismatch: ticket={source_pid} req={req_pid}")

                conn.pid         = source_pid
                conn.session_key = session_key
                conn.rc4         = RC4Stream(session_key)
                conn.state       = Connection.STATE_CONNECTED

                ack_payload = struct.pack('<II', 4, (check_val + 1) & 0xFFFFFFFF)
                log.info("[%s] CONNECT OK pid=%d from %s", self.mode, source_pid, addr)

            except Exception as e:
                log.error("[%s] CONNECT ticket error from %s: %s", self.mode, addr, e)
                self.conns.pop(addr, None)
                return

        ack                     = pkt.Packet(ptype=pkt.TYPE_CONNECT,
                                              flags=pkt.FLAG_ACK | pkt.FLAG_HAS_SIZE)
        ack.src                 = conn.server_vport
        ack.dst                 = conn.client_vport
        ack.session_id          = conn.session_id
        ack.seq_id              = 1
        ack.conn_sig            = bytes(16)
        ack.minor_version       = conn.minor_version
        ack.supported_functions = p.supported_functions
        ack.max_substream_id    = p.max_substream_id
        ack.payload             = ack_payload

        raw = pkt.encode(ack, config.ACCESS_KEY, b'', conn.client_conn_sig)
        self.transport.sendto(raw, addr)
        asyncio.ensure_future(self._ping_loop(addr, conn))

    def _data(self, p, addr, conn):
        if p.has_flag(pkt.FLAG_NEED_ACK):
            self._ack(conn, p)
        if not p.payload:
            return

        seq = p.seq_id
        if seq in conn.seen_data_seqs:
            log.debug("[%s] duplicate DATA seq=%d ignored (already processed)",
                      self.mode, seq)
            return
        conn.seen_data_seqs.add(seq)

        if len(conn.seen_data_seqs) > 256:
            conn.seen_data_seqs = set(sorted(conn.seen_data_seqs)[-128:])

        raw = conn.rc4.decrypt(p.payload) if conn.rc4 else p.payload

        try:
            req = rmc_mod.decode_request(raw)
        except Exception as e:
            log.warning("[%s] bad RMC from %s: %s (payload=%s)",
                        self.mode, addr, e, raw[:16].hex())
            return

        log.debug("[%s] RMC proto=0x%02X method=0x%02X call=%d pid=%d",
                  self.mode, req.protocol, req.method, req.call_id, conn.pid)

        asyncio.ensure_future(self._dispatch(req, conn))

    async def _dispatch(self, req, conn):
        try:
            resp = await self.dispatch(req, conn.pid, conn.addr)
        except Exception:
            log.exception("[%s] dispatch error", self.mode)
            resp = rmc_mod.encode_error(req.protocol, req.method,
                                         req.call_id, 0x80010002)
        await self._send_data(resp, conn)

    async def _send_data(self, payload, conn):
        enc  = conn.rc4.encrypt(payload) if conn.rc4 else payload
        seq  = conn.data_seq
        conn.data_seq = (conn.data_seq + 1) & 0xFFFF

        p             = pkt.Packet(ptype=pkt.TYPE_DATA,
                                    flags=pkt.FLAG_RELIABLE | pkt.FLAG_NEED_ACK | pkt.FLAG_HAS_SIZE)
        p.src         = conn.server_vport
        p.dst         = conn.client_vport
        p.session_id  = conn.session_id
        p.seq_id      = seq
        p.fragment_id = 0
        p.payload     = enc

        raw = pkt.encode(p, config.ACCESS_KEY, conn.session_key, conn.client_conn_sig)
        key = (pkt.TYPE_DATA, seq)
        self.transport.sendto(raw, conn.addr)
        conn.pending[key] = raw

        delay = 0.4
        for _ in range(config.PRUDP_RESEND_LIMIT):
            await asyncio.sleep(delay)
            if key not in conn.pending:
                return
            log.debug("[%s] resend DATA seq=%d -> %s", self.mode, seq, conn.addr)
            self.transport.sendto(raw, conn.addr)
            delay = min(delay * 1.5, 2.0)

        conn.pending.pop(key, None)
        log.warning("[%s] DATA seq=%d unacknowledged", self.mode, seq)

    async def _ping_loop(self, addr, conn):

        while conn.addr in self.conns and self.conns[conn.addr] is conn:
            await asyncio.sleep(PING_INTERVAL)
            if time.monotonic() - conn.last_ack > CONNECTION_IDLE_TIMEOUT:
                log.info("[%s] idle timeout pid=%d %s", self.mode, conn.pid, conn.addr)
                self.conns.pop(conn.addr, None)
                conn.pending.clear()
                return

class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, server):
        self.server = server

    def connection_made(self, transport):
        self.server.transport = transport

    def datagram_received(self, data, addr):
        self.server.process(data, addr)

    def error_received(self, exc):
        log.warning("UDP error: %s", exc)
