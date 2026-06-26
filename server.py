import asyncio
import logging
import os
import sys

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


async def main():
    config.load()

    log.info("Initialising…")
    import anyio
    await anyio.to_thread.run_sync(db.init_mongo)
    await anyio.to_thread.run_sync(db.init_sqlite)
    s3_store.init()
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
