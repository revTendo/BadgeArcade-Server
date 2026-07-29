from django.utils import timezone

from .models import Account, NexAccount, Device, AccountBan
from . import mailer

def _device_identifiers(pid):
    ids = []
    nex = NexAccount.objects.filter(pid=str(pid)).exclude(serial_hash__isnull=True).first()
    if nex and nex.serial_hash:
        ids.append(nex.serial_hash)
    dev = Device.objects.filter(pid=str(pid)).exclude(device_id__isnull=True).order_by("-id").first()
    if dev and dev.device_id:
        ids.append(str(dev.device_id))
    return ids

def expire_stale_bans():
    AccountBan.objects.filter(
        active=True, ban_type="temp", expires_at__isnull=False, expires_at__lte=timezone.now()
    ).update(active=False, lifted_at=timezone.now(), lifted_by="system (expired)")

def active_ban(pid):
    expire_stale_bans()
    return AccountBan.objects.filter(pid=str(pid), active=True).order_by("-created_at").first()

def issue_ban(pid, ban_type, reason="", banned_by="revTendo Staff", expires_at=None):
    if ban_type not in ("account", "temp", "device"):
        raise ValueError("invalid ban_type: %s" % ban_type)

    account = Account.objects.filter(pid=str(pid)).first()
    if not account:
        raise ValueError("no account for pid %s" % pid)

    expiry = expires_at if ban_type == "temp" else None

    if ban_type == "device":
        ids = _device_identifiers(pid)
        if not ids:
            raise ValueError("no device on record for pid %s" % pid)
        for device_id in ids:
            AccountBan.objects.create(
                pid=str(pid), ban_type=ban_type, reason=reason or "",
                banned_by=banned_by or "revTendo Staff", device_id=device_id,
                active=True, created_at=timezone.now(), expires_at=expiry,
            )
    else:
        AccountBan.objects.create(
            pid=str(pid), ban_type=ban_type, reason=reason or "",
            banned_by=banned_by or "revTendo Staff", device_id=None,
            active=True, created_at=timezone.now(), expires_at=expiry,
        )

    Account.objects.filter(pid=str(pid)).update(flag_active=False)

    emailed = False
    if account.email_address:
        try:
            mailer.send_account_ban_email(
                account.email_address,
                account.username or account.user_id or account.pid,
                ban_type="account" if ban_type == "temp" else ban_type,
                reason=reason,
                banned_by=banned_by,
                expires_at=expiry.strftime("%Y-%m-%d %H:%M UTC") if expiry else None,
            )
            emailed = True
        except Exception:
            emailed = False

    return emailed

def lift_bans(pid, lifted_by="revTendo Staff"):
    n = AccountBan.objects.filter(pid=str(pid), active=True).update(
        active=False, lifted_at=timezone.now(), lifted_by=lifted_by or "revTendo Staff"
    )
    if not AccountBan.objects.filter(pid=str(pid), active=True).exists():
        Account.objects.filter(pid=str(pid)).update(flag_active=True)
    return n

def ban_raw_device(device_id, reason="", banned_by="revTendo Staff", pid=None):
    device_id = (device_id or "").strip()
    if not device_id:
        raise ValueError("device_id is required")
    existing = AccountBan.objects.filter(device_id=device_id, ban_type="device", active=True).first()
    if existing:
        raise ValueError("device %s is already banned (ban id %s)" % (device_id, existing.id))
    AccountBan.objects.create(
        pid=str(pid) if pid else "0",
        ban_type="device", reason=reason or "",
        banned_by=banned_by or "revTendo Staff", device_id=device_id,
        active=True, created_at=timezone.now(), expires_at=None,
    )
    if pid:
        Account.objects.filter(pid=str(pid)).update(flag_active=False)
    return device_id

def lift_device(device_id, lifted_by="revTendo Staff"):
    device_id = (device_id or "").strip()
    return AccountBan.objects.filter(device_id=device_id, ban_type="device", active=True).update(
        active=False, lifted_at=timezone.now(), lifted_by=lifted_by or "revTendo Staff"
    )
