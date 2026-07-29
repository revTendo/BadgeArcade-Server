from django.db import models

class Account(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.CharField(max_length=50, null=True, blank=True)
    pid = models.CharField(max_length=50)
    username = models.CharField(max_length=50, null=True, blank=True)
    username_lower = models.CharField(max_length=50, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, null=True, blank=True)
    country = models.CharField(max_length=5, null=True, blank=True)
    language = models.CharField(max_length=10, null=True, blank=True)
    region = models.CharField(max_length=20, null=True, blank=True)
    email_address = models.CharField(max_length=255, null=True, blank=True)
    email_primary = models.BooleanField(default=False)
    email_parent = models.BooleanField(default=False)
    email_reachable = models.BooleanField(default=False)
    email_validated = models.BooleanField(default=False)
    email_validated_date = models.DateTimeField(null=True, blank=True)
    email_id = models.CharField(max_length=50, null=True, blank=True)
    timezone_name = models.CharField(max_length=50, null=True, blank=True)
    timezone_offset = models.IntegerField(null=True, blank=True)
    mii_name = models.CharField(max_length=50, null=True, blank=True)
    mii_primary = models.BooleanField(default=False)
    mii_data = models.TextField(null=True, blank=True)
    mii_id = models.CharField(max_length=50, null=True, blank=True)
    mii_hash = models.CharField(max_length=50, null=True, blank=True)
    mii_image_id = models.CharField(max_length=50, null=True, blank=True)
    flag_active = models.BooleanField(default=True)
    flag_marketing = models.BooleanField(default=False)
    flag_off_device = models.BooleanField(default=False)
    identification_email_code = models.CharField(max_length=10, null=True, blank=True)
    identification_email_token = models.CharField(max_length=100, null=True, blank=True)
    device_id = models.CharField(max_length=50, null=True, blank=True)
    creation_date = models.DateTimeField(null=True, blank=True)
    updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "accounts"
        verbose_name = "PNID account"
        verbose_name_plural = "PNID accounts"

    def __str__(self):
        return (self.username or self.user_id or self.pid or str(self.id))

class NexAccount(models.Model):
    id = models.AutoField(primary_key=True)
    pid = models.CharField(max_length=50)
    password = models.CharField(max_length=255, null=True, blank=True)
    mac_hash = models.CharField(max_length=255, null=True, blank=True)
    serial_hash = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "nex_accounts"
        verbose_name = "NEX account"

    def __str__(self):
        return "NEX " + str(self.pid)

class Token(models.Model):
    id = models.AutoField(primary_key=True)
    pid = models.CharField(max_length=50)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    access_expires_at = models.DateTimeField(null=True, blank=True)
    refresh_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "tokens"

    def __str__(self):
        return "Token for " + str(self.pid)

class ServiceToken(models.Model):
    id = models.AutoField(primary_key=True)
    pid = models.CharField(max_length=50)
    client_id = models.CharField(max_length=100, null=True, blank=True)
    token = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_tokens"

    def __str__(self):
        return "Service token for " + str(self.pid)

class Device(models.Model):
    id = models.AutoField(primary_key=True)
    pid = models.CharField(max_length=50, null=True, blank=True)
    device_id = models.CharField(max_length=50, null=True, blank=True)
    language = models.CharField(max_length=10, null=True, blank=True)
    platform_id = models.CharField(max_length=20, null=True, blank=True)
    region = models.CharField(max_length=20, null=True, blank=True)
    serial_number = models.CharField(max_length=50, null=True, blank=True)
    system_version = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    type = models.CharField(max_length=20, null=True, blank=True)
    updated_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "devices"

    def __str__(self):
        return str(self.device_id or self.id)

class DeviceAttribute(models.Model):
    id = models.AutoField(primary_key=True)
    pid = models.CharField(max_length=50, null=True, blank=True)
    device_id = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    value = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "device_attributes"

    def __str__(self):
        return str(self.name)

class GameServer(models.Model):
    id = models.AutoField(primary_key=True)
    client_id = models.CharField(max_length=64)
    name = models.CharField(max_length=100, null=True, blank=True)
    host = models.CharField(max_length=255, null=True, blank=True)
    port = models.IntegerField(null=True, blank=True)
    aes_key = models.CharField(max_length=255, null=True, blank=True)
    device = models.CharField(max_length=10, null=True, blank=True)
    is_public = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "game_servers"

    def __str__(self):
        return self.name or str(self.client_id or self.id)

class ApiKey(models.Model):
    id = models.AutoField(primary_key=True)
    api_key = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "api_keys"

    def __str__(self):
        return "API key " + str(self.id)

class AccountBan(models.Model):
    BAN_TYPES = (("account", "Account ban"), ("temp", "Temporary ban"), ("device", "Console ban"))
    id = models.AutoField(primary_key=True)
    pid = models.CharField(max_length=50)
    ban_type = models.CharField(max_length=10, choices=BAN_TYPES)
    reason = models.CharField(max_length=500, blank=True, default="")
    banned_by = models.CharField(max_length=64, default="revTendo Staff")
    device_id = models.CharField(max_length=64, null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    lifted_at = models.DateTimeField(null=True, blank=True)
    lifted_by = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "account_bans"
        verbose_name = "ban"
        verbose_name_plural = "bans"

    def __str__(self):
        return "%s ban on pid %s" % (self.ban_type, self.pid)
