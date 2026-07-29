import os
import ssl
import smtplib
from email.message import EmailMessage

def _config():
    return {
        "host": os.environ.get("ACCOUNTS_SMTP_HOST", "mail.wiimart.org"),
        "port": int(os.environ.get("ACCOUNTS_SMTP_PORT", "587")),
        "user": os.environ.get("ACCOUNTS_SMTP_USER", "support@revtendo.com"),
        "password": os.environ.get("ACCOUNTS_SMTP_PASSWORD", ""),
        "from": os.environ.get("ACCOUNTS_SMTP_FROM", "revTendo Accounts <support@revtendo.com>"),
    }

def _send(to_address, subject, body):
    cfg = _config()
    msg = EmailMessage()
    msg["From"] = cfg["from"]
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
        server.ehlo()
        try:
            server.starttls(context=context)
            server.ehlo()
        except smtplib.SMTPNotSupportedError:
            pass
        if cfg["user"] and cfg["password"]:
            server.login(cfg["user"], cfg["password"])
        server.send_message(msg)

def send_verification_email(to_address, username, code):
    body = "\n".join([
        "Hello, %s!" % username,
        "",
        "Thank you for creating a revID.",
        "",
        "Enter the following verification code on your Nintendo 3DS to activate your account:",
        "",
        "    %s" % code,
        "",
        "This code expires when you request a new one.",
        "",
        "If you did not create this account, ignore this email.",
        "",
        "- The revTendo team",
    ])
    _send(to_address, "Verify your revTendo Network ID (revID)", body)

def send_password_reset_email(to_address, username, temp_password):
    body = "\n".join([
        "Hello, %s!" % username,
        "",
        "We received a request to reset the password for your revID.",
        "",
        "Your temporary password is:",
        "",
        "    %s" % temp_password,
        "",
        "Log into your Nintendo 3DS using this password. You may change it in your Nintendo Network ID Settings.",
        "",
        "If you did not request a password reset, ignore this email.",
        "Your password will not be changed unless you log in with the temporary password above.",
        "",
        "- The revTendo team",
    ])
    _send(to_address, "Reset your revTendo Network ID (revID) Password", body)

def send_account_ban_email(to_address, username, ban_type="account", reason=None, banned_by=None, expires_at=None):
    type_label = "Console Ban" if ban_type == "device" else "Account Ban"
    expiry = expires_at if expires_at else "Permanent"
    tail = ("Your console has been banned from all of revTendo Network services."
            if ban_type == "device"
            else "Your account has been banned from revTendo Network services. You will not be able to access online features until the ban expires.")
    body = "\n".join([
        "Hello, %s!" % username,
        "",
        "Your revID has received a %s." % type_label,
        "",
        "Ban type:   %s" % type_label,
        "Reason:     %s" % (reason or "No reason provided"),
        "Issued by:  %s" % (banned_by or "The revTendo Moderation Team"),
        "Expires:    %s" % expiry,
        "",
        tail,
        "",
        "If you believe this is a mistake, please contact us on our Discord or send an email at support@revtendo.com",
        "",
        "- The revTendo Team",
    ])
    _send(to_address, "Your revTendo Network ID (revID) has been suspended", body)
