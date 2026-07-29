import asyncio
import logging
import os
import sys
import threading

import config
import db
import s3_store
from nex.server  import PRUDPServer
from nex.crypto  import derive_kerberos_key
from protocols   import auth, secure

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("badge_arcade")

async def auth_dispatch(req, pid, addr):
    return await auth.handle(req.method, req.call_id, req.params)

async def secure_dispatch(req, pid, addr):
    from protocols.secure import (
        PROTO_SECURE, PROTO_DS, PROTO_SHOP,
        handle_secure, handle_datastore, handle_shop,
    )
    if req.protocol == PROTO_SECURE:
        return await handle_secure(req.method, req.call_id, req.params, pid, addr)
    elif req.protocol == PROTO_DS:
        return await handle_datastore(req.method, req.call_id, req.params, pid)
    elif req.protocol == PROTO_SHOP:
        return await handle_shop(req.method, req.call_id, req.params, pid)
    else:
        from nex.rmc import encode_error
        log.warning("[Secure] Unknown protocol 0x%X", req.protocol)
        return encode_error(req.protocol, req.method, req.call_id, 0x80010002)

def start_eshop():

    enabled = os.environ.get("ESHOP_ENABLED", "1").lower() in ("1", "true", "yes")
    if not enabled:
        log.info("eShop disabled (ESHOP_ENABLED=0)")
        return

    host = os.environ.get("ESHOP_HOST", "0.0.0.0")
    port = int(os.environ.get("ESHOP_PORT", "8724"))
    cert = os.environ.get("ESHOP_SSL_CERT", "./eshop/cert.pem")
    key  = os.environ.get("ESHOP_SSL_KEY",  "./eshop/cert.key")

    if not (os.path.isfile(cert) and os.path.isfile(key)):
        try:
            from eshop import certs as _certs
            server_ip = config.file_server_host()
            cert, key = _certs.ensure_certs(cert, key, server_ip=server_ip)
        except Exception:
            log.exception("eShop cert auto-generation failed")
            cert, key = None, None

    try:
        import eshop
        app = eshop.build_app()
    except Exception:
        log.exception("eShop failed to initialise — purchases unavailable.")
        return

    ssl_context = (cert, key) if (cert and key) else None
    if ssl_context is None:
        log.warning("eShop running WITHOUT TLS (set ESHOP_SSL_CERT/ESHOP_SSL_KEY). "
                    "The 3DS expects HTTPS for shop endpoints.")

    def _run():
        try:
            app.run(host=host, port=port, ssl_context=ssl_context,
                    threaded=True, use_reloader=False, debug=False)
        except Exception:
            log.exception("eShop server crashed")

    t = threading.Thread(target=_run, daemon=True, name="eshop")
    t.start()
    scheme = "https" if ssl_context else "http"
    log.info("eShop (commerce) on %s://%s:%d", scheme, host, port)

async def main():
    config.load()

    log.info("Initialising…")
    import anyio
    await anyio.to_thread.run_sync(db.init_mongo)
    await anyio.to_thread.run_sync(db.init_sqlite)
    s3_store.init()

    start_eshop()

    log.info("All backends ready")

    server_key = derive_kerberos_key(2, config.kerberos_password().encode())

    auth_srv   = PRUDPServer(config.AUTH_PORT,   'auth',   auth_dispatch)
    secure_srv = PRUDPServer(config.SECURE_PORT, 'secure', secure_dispatch, server_key)

    await auth_srv.start()
    await secure_srv.start()

    log.info("Auth   server on port %d", config.AUTH_PORT)
    log.info("Secure server on port %d", config.SECURE_PORT)

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        auth_srv.stop()
        secure_srv.stop()
        log.info("Stopped")

if __name__ == "__main__":
    asyncio.run(main())
