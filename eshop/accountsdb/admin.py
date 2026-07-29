from django.apps import apps
from django.contrib import admin, messages
from django.db import models as dj_models
from django.utils import timezone
from django import forms

from .models import Account, Token, AccountBan, Device, NexAccount
from . import moderation
from datetime import timedelta
from . import mailer
from . import passwords

_LONG_FIELDS = {"mii_data", "aes_key", "token", "access_token", "refresh_token", "password", "identification_email_token"}

def _list_display(model):
    fields = []
    for f in model._meta.concrete_fields:
        if isinstance(f, dj_models.TextField):
            continue
        if f.name in _LONG_FIELDS:
            continue
        fields.append(f.name)
        if len(fields) >= 8:
            break
    if "id" not in fields:
        fields.insert(0, "id")
    return fields

def _search_fields(model):
    return [f.name for f in model._meta.concrete_fields
            if isinstance(f, (dj_models.CharField, dj_models.TextField))]

def _list_filter(model):
    return [f.name for f in model._meta.concrete_fields
            if isinstance(f, dj_models.BooleanField)]

def _make_admin(model):
    attrs = {
        "list_display": _list_display(model),
        "search_fields": _search_fields(model),
        "list_filter": _list_filter(model),
        "list_per_page": 50,
        "save_on_top": True,
    }
    return type(model.__name__ + "Admin", (admin.ModelAdmin,), attrs)

class AccountAdminForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Set new password",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Type a plain password to set it. Hashed the same way the console expects. Leave blank to keep current.",
    )

    class Meta:
        model = Account
        fields = "__all__"

class AccountAdmin(admin.ModelAdmin):
    form = AccountAdminForm
    save_on_top = True
    list_display = ("id", "username", "pid", "country", "email_address", "email_validated", "flag_active", "updated")
    list_display_links = ("id", "username")
    list_filter = ("flag_active", "email_validated", "email_primary", "flag_marketing", "flag_off_device", "country")
    search_fields = ("username", "username_lower", "pid", "user_id", "email_address", "mii_name", "device_id")
    list_per_page = 50
    readonly_fields = ("password", "creation_date", "updated", "email_validated_date")
    actions = (
        "account_ban", "temp_ban_24h", "temp_ban_7d", "console_ban", "lift_all_bans",
        "activate_accounts", "deactivate_accounts",
        "resend_verification_email", "mark_email_verified", "mark_email_unverified",
        "reset_password_and_email", "revoke_tokens",
    )
    fieldsets = (
        ("Identity", {"fields": ("user_id", "pid", "username", "username_lower", "device_id")}),
        ("Security", {"fields": ("password", "new_password")}),
        ("Email & verification", {"fields": (
            "email_address", "email_primary", "email_parent", "email_reachable",
            "email_validated", "email_validated_date", "email_id",
            "identification_email_code", "identification_email_token")}),
        ("Profile", {"fields": ("birthdate", "gender", "country", "language", "region", "timezone_name", "timezone_offset")}),
        ("Mii", {"fields": ("mii_name", "mii_primary", "mii_id", "mii_hash", "mii_image_id", "mii_data"), "classes": ("collapse",)}),
        ("Flags", {"fields": ("flag_active", "flag_marketing", "flag_off_device")}),
        ("Timestamps", {"fields": ("creation_date", "updated"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        new_password = form.cleaned_data.get("new_password")
        if new_password:
            try:
                obj.password = passwords.make_stored_password(new_password, obj.pid)
                messages.success(request, "Password updated for %s." % (obj.username or obj.pid))
            except Exception as e:
                messages.error(request, "Could not set password: %s" % e)
        super().save_model(request, obj, form, change)

    def _issue(self, request, queryset, ban_type, hours=None):
        by = request.user.get_username()
        ok = failed = emailed = 0
        for acc in queryset:
            expires = timezone.now() + timedelta(hours=hours) if hours else None
            try:
                sent = moderation.issue_ban(acc.pid, ban_type, reason="", banned_by=by, expires_at=expires)
                ok += 1
                emailed += 1 if sent else 0
            except Exception as e:
                failed += 1
                self.message_user(request, "Ban failed for pid %s: %s" % (acc.pid, e), messages.WARNING)
        label = {"account": "account ban", "temp": "temp ban", "device": "console ban"}[ban_type]
        self.message_user(request, "Issued %d %s(s); %d email(s) sent; %d failed." % (ok, label, emailed, failed),
                          messages.SUCCESS if not failed else messages.WARNING)

    @admin.action(description="Ban: permanent account ban (+ email)")
    def account_ban(self, request, queryset):
        self._issue(request, queryset, "account")

    @admin.action(description="Ban: temporary (24 hours) (+ email)")
    def temp_ban_24h(self, request, queryset):
        self._issue(request, queryset, "temp", hours=24)

    @admin.action(description="Ban: temporary (7 days) (+ email)")
    def temp_ban_7d(self, request, queryset):
        self._issue(request, queryset, "temp", hours=24 * 7)

    @admin.action(description="Ban: console ban (all accounts on the device) (+ email)")
    def console_ban(self, request, queryset):
        self._issue(request, queryset, "device")

    @admin.action(description="Lift all active bans for selected")
    def lift_all_bans(self, request, queryset):
        by = request.user.get_username()
        total = 0
        for acc in queryset:
            total += moderation.lift_bans(acc.pid, lifted_by=by)
        self.message_user(request, "Lifted %d ban(s)." % total, messages.SUCCESS)

    @admin.action(description="Activate (flag_active = on)")
    def activate_accounts(self, request, queryset):
        n = queryset.update(flag_active=True)
        self.message_user(request, "Activated %d account(s)." % n, messages.SUCCESS)

    @admin.action(description="Deactivate (flag_active = off)")
    def deactivate_accounts(self, request, queryset):
        n = queryset.update(flag_active=False)
        self.message_user(request, "Deactivated %d account(s)." % n, messages.SUCCESS)

    @admin.action(description="Ban (deactivate) and email the user")
    def ban_and_email(self, request, queryset):
        sent = 0
        for acc in queryset:
            acc.flag_active = False
            acc.save()
            if acc.email_address:
                try:
                    mailer.send_account_ban_email(acc.email_address, acc.username or acc.user_id or acc.pid,
                                                  ban_type="account", banned_by=request.user.get_username())
                    sent += 1
                except Exception as e:
                    self.message_user(request, "Ban email failed for %s: %s" % (acc.pid, e), messages.WARNING)
        self.message_user(request, "Banned %d account(s); %d email(s) sent." % (queryset.count(), sent), messages.SUCCESS)

    @admin.action(description="Resend verification email (new code)")
    def resend_verification_email(self, request, queryset):
        sent = 0
        for acc in queryset:
            if not acc.email_address:
                self.message_user(request, "No email on file for %s." % acc.pid, messages.WARNING)
                continue
            code = passwords.generate_email_code()
            acc.identification_email_code = code
            acc.save()
            try:
                mailer.send_verification_email(acc.email_address, acc.username or acc.user_id or acc.pid, code)
                sent += 1
            except Exception as e:
                self.message_user(request, "Verification email failed for %s: %s" % (acc.pid, e), messages.WARNING)
        self.message_user(request, "Sent %d verification email(s)." % sent, messages.SUCCESS)

    @admin.action(description="Mark email as verified")
    def mark_email_verified(self, request, queryset):
        n = queryset.update(email_validated=True, email_reachable=True, email_validated_date=timezone.now())
        self.message_user(request, "Marked %d email(s) verified." % n, messages.SUCCESS)

    @admin.action(description="Mark email as unverified")
    def mark_email_unverified(self, request, queryset):
        n = queryset.update(email_validated=False, email_validated_date=None)
        self.message_user(request, "Marked %d email(s) unverified." % n, messages.SUCCESS)

    @admin.action(description="Reset password and email a temporary one")
    def reset_password_and_email(self, request, queryset):
        sent = 0
        for acc in queryset:
            if not acc.email_address:
                self.message_user(request, "No email on file for %s; skipped." % acc.pid, messages.WARNING)
                continue
            temp = passwords.generate_temp_password()
            try:
                acc.password = passwords.make_stored_password(temp, acc.pid)
                acc.save()
                mailer.send_password_reset_email(acc.email_address, acc.username or acc.user_id or acc.pid, temp)
                sent += 1
            except Exception as e:
                self.message_user(request, "Password reset failed for %s: %s" % (acc.pid, e), messages.WARNING)
        self.message_user(request, "Reset and emailed %d password(s)." % sent, messages.SUCCESS)

    @admin.action(description="Revoke tokens (force logout)")
    def revoke_tokens(self, request, queryset):
        total = 0
        for acc in queryset:
            total += Token.objects.filter(pid=acc.pid).delete()[0]
        self.message_user(request, "Revoked %d token(s)." % total, messages.SUCCESS)

class AccountBanForm(forms.ModelForm):
    duration_hours = forms.IntegerField(
        label="Temp ban duration (hours)", required=False,
        help_text="Only for ban_type = temp. Leave blank for permanent account/console bans.",
    )
    raw_device_id = forms.CharField(
        label="Raw device identifier", required=False,
        help_text="Paste a device_id (from an NNAS/oauth log) or a csHash serial hash (from a NASC log) "
                  "to ban that console directly, even with no account on file. Overrides pid/ban_type: "
                  "this always creates a device ban on the exact string you paste.",
    )

    class Meta:
        model = AccountBan
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("raw_device_id") and not cleaned.get("pid"):
            raise forms.ValidationError("Provide either a pid, or a raw device identifier.")
        return cleaned

class AccountBanAdmin(admin.ModelAdmin):
    form = AccountBanForm
    save_on_top = True
    list_display = ("id", "pid", "ban_type", "reason", "banned_by", "active", "created_at", "expires_at", "lifted_by")
    list_display_links = ("id", "pid")
    list_filter = ("ban_type", "active")
    search_fields = ("pid", "reason", "banned_by", "device_id")
    list_per_page = 50
    readonly_fields = ("created_at", "lifted_at")
    actions = ("lift_selected",)

    def save_model(self, request, obj, form, change):
        if not change:
            by = request.user.get_username()
            raw = (form.cleaned_data.get("raw_device_id") or "").strip()
            if raw:
                try:
                    moderation.ban_raw_device(raw, reason=obj.reason, banned_by=by,
                                              pid=(obj.pid if obj.pid and obj.pid != "0" else None))
                    messages.success(request, "Device ban issued for identifier %s." % raw)
                except Exception as e:
                    messages.error(request, "Could not ban device: %s" % e)
                return
            hours = form.cleaned_data.get("duration_hours")
            expires = timezone.now() + timedelta(hours=hours) if (obj.ban_type == "temp" and hours) else None
            try:
                moderation.issue_ban(obj.pid, obj.ban_type, reason=obj.reason,
                                     banned_by=by, expires_at=expires)
                messages.success(request, "Ban issued for pid %s." % obj.pid)
            except Exception as e:
                messages.error(request, "Could not issue ban: %s" % e)
            return
        super().save_model(request, obj, form, change)

    @admin.action(description="Lift selected bans")
    def lift_selected(self, request, queryset):
        by = request.user.get_username()
        total = 0
        for ban in queryset:
            if (ban.pid in (None, "", "0")) and ban.device_id:
                total += moderation.lift_device(ban.device_id, lifted_by=by)
        pids = set(p for p in queryset.values_list("pid", flat=True) if p and p != "0")
        for pid in pids:
            total += moderation.lift_bans(pid, lifted_by=by)
        self.message_user(request, "Lifted %d ban(s) across %d account(s)." % (total, len(pids)), messages.SUCCESS)

admin.site.register(AccountBan, AccountBanAdmin)
admin.site.register(Account, AccountAdmin)

for _model in apps.get_app_config("accountsdb").get_models():
    if _model in (Account, AccountBan):
        continue
    try:
        admin.site.register(_model, _make_admin(_model))
    except admin.sites.AlreadyRegistered:
        pass

from accountsdb import gameserver_admin
