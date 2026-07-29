import logging
import os
import platform
import shutil
import stat
import subprocess
import urllib.request

log = logging.getLogger("eshop.certs")

SHOP_HOSTS = [
    "ecs.c.shop.nintendowifi.net",
    "cas.c.shop.nintendowifi.net",
    "ias.c.shop.nintendowifi.net",
    "ninja.ctr.shop.nintendo.net",
    "localhost",
    "127.0.0.1",
]

_MKCERT_RELEASES = {
    ("Linux", "x86_64"): "mkcert-v1.4.4-linux-amd64",
    ("Linux", "aarch64"): "mkcert-v1.4.4-linux-arm64",
    ("Darwin", "x86_64"): "mkcert-v1.4.4-darwin-amd64",
    ("Darwin", "arm64"): "mkcert-v1.4.4-darwin-arm64",
    ("Windows", "AMD64"): "mkcert-v1.4.4-windows-amd64.exe",
}
_MKCERT_BASE = "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/"

def _find_or_fetch_mkcert(workdir):
    found = shutil.which("mkcert")
    if found:
        return found

    key = (platform.system(), platform.machine())
    asset = _MKCERT_RELEASES.get(key)
    if not asset:
        log.warning("No prebuilt mkcert for %s; install mkcert manually.", key)
        return None

    dest = os.path.join(workdir, "mkcert.exe" if key[0] == "Windows" else "mkcert")
    if os.path.isfile(dest):
        return dest

    url = _MKCERT_BASE + asset
    log.info("Downloading mkcert from %s", url)
    try:
        urllib.request.urlretrieve(url, dest)
        if key[0] != "Windows":
            os.chmod(dest, os.stat(dest).st_mode | stat.S_IEXEC)
        return dest
    except Exception:
        log.exception("Failed to download mkcert")
        return None

def ensure_certs(cert_path, key_path, server_ip=None):
    if cert_path and key_path and os.path.isfile(cert_path) and os.path.isfile(key_path):
        return cert_path, key_path

    cert_path = cert_path or "./eshop/cert.pem"
    key_path = key_path or "./eshop/cert.key"
    workdir = os.path.dirname(os.path.abspath(cert_path)) or "."
    os.makedirs(workdir, exist_ok=True)

    mkcert = _find_or_fetch_mkcert(workdir)
    if not mkcert:
        log.warning("mkcert unavailable; cannot auto-generate certs.")
        return None, None

    hosts = list(SHOP_HOSTS)
    if server_ip and server_ip not in hosts:
        hosts.append(server_ip)

    env = dict(os.environ)
    env.setdefault("CAROOT", os.path.join(workdir, "mkcert-ca"))
    os.makedirs(env["CAROOT"], exist_ok=True)

    try:
        subprocess.run([mkcert, "-install"], env=env, check=False, capture_output=True, text=True)
        result = subprocess.run(
            [mkcert, "-cert-file", cert_path, "-key-file", key_path, *hosts],
            env=env, check=True, capture_output=True, text=True,
        )
        log.info("mkcert generated certs for: %s", ", ".join(hosts))
        if result.stdout:
            log.debug(result.stdout.strip())
        return cert_path, key_path
    except subprocess.CalledProcessError as e:
        log.error("mkcert failed: %s", e.stderr or e)
        return None, None
    except Exception:
        log.exception("cert generation error")
        return None, None
