

from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('user_id', models.CharField(blank=True, max_length=50, null=True)),
                ('pid', models.CharField(max_length=50)),
                ('username', models.CharField(blank=True, max_length=50, null=True)),
                ('username_lower', models.CharField(blank=True, max_length=50, null=True)),
                ('password', models.CharField(blank=True, max_length=255, null=True)),
                ('birthdate', models.DateField(blank=True, null=True)),
                ('gender', models.CharField(blank=True, max_length=1, null=True)),
                ('country', models.CharField(blank=True, max_length=5, null=True)),
                ('language', models.CharField(blank=True, max_length=10, null=True)),
                ('region', models.CharField(blank=True, max_length=20, null=True)),
                ('email_address', models.CharField(blank=True, max_length=255, null=True)),
                ('email_primary', models.BooleanField(default=False)),
                ('email_parent', models.BooleanField(default=False)),
                ('email_reachable', models.BooleanField(default=False)),
                ('email_validated', models.BooleanField(default=False)),
                ('email_validated_date', models.DateTimeField(blank=True, null=True)),
                ('email_id', models.CharField(blank=True, max_length=50, null=True)),
                ('timezone_name', models.CharField(blank=True, max_length=50, null=True)),
                ('timezone_offset', models.IntegerField(blank=True, null=True)),
                ('mii_name', models.CharField(blank=True, max_length=50, null=True)),
                ('mii_primary', models.BooleanField(default=False)),
                ('mii_data', models.TextField(blank=True, null=True)),
                ('mii_id', models.CharField(blank=True, max_length=50, null=True)),
                ('mii_hash', models.CharField(blank=True, max_length=50, null=True)),
                ('mii_image_id', models.CharField(blank=True, max_length=50, null=True)),
                ('flag_active', models.BooleanField(default=True)),
                ('flag_marketing', models.BooleanField(default=False)),
                ('flag_off_device', models.BooleanField(default=False)),
                ('identification_email_code', models.CharField(blank=True, max_length=10, null=True)),
                ('identification_email_token', models.CharField(blank=True, max_length=100, null=True)),
                ('device_id', models.CharField(blank=True, max_length=50, null=True)),
                ('creation_date', models.DateTimeField(blank=True, null=True)),
                ('updated', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'PNID account',
                'verbose_name_plural': 'PNID accounts',
                'db_table': 'accounts',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ApiKey',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('api_key', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'api_keys',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('pid', models.CharField(blank=True, max_length=50, null=True)),
                ('device_id', models.CharField(blank=True, max_length=50, null=True)),
                ('language', models.CharField(blank=True, max_length=10, null=True)),
                ('platform_id', models.CharField(blank=True, max_length=20, null=True)),
                ('region', models.CharField(blank=True, max_length=20, null=True)),
                ('serial_number', models.CharField(blank=True, max_length=50, null=True)),
                ('system_version', models.CharField(blank=True, max_length=20, null=True)),
                ('status', models.CharField(blank=True, max_length=20, null=True)),
                ('type', models.CharField(blank=True, max_length=20, null=True)),
                ('updated_by', models.CharField(blank=True, max_length=50, null=True)),
            ],
            options={
                'db_table': 'devices',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DeviceAttribute',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('pid', models.CharField(blank=True, max_length=50, null=True)),
                ('device_id', models.CharField(blank=True, max_length=50, null=True)),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('value', models.TextField(blank=True, null=True)),
                ('created_date', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'device_attributes',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='GameServer',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('client_id', models.CharField(blank=True, max_length=100, null=True)),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('aes_key', models.CharField(blank=True, max_length=255, null=True)),
                ('is_public', models.BooleanField(default=False)),
                ('maintenance_mode', models.BooleanField(default=False)),
                ('device', models.CharField(blank=True, max_length=50, null=True)),
            ],
            options={
                'db_table': 'game_servers',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='NexAccount',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('pid', models.CharField(max_length=50)),
                ('password', models.CharField(blank=True, max_length=255, null=True)),
                ('mac_hash', models.CharField(blank=True, max_length=255, null=True)),
                ('serial_hash', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'verbose_name': 'NEX account',
                'db_table': 'nex_accounts',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ServiceToken',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('pid', models.CharField(max_length=50)),
                ('client_id', models.CharField(blank=True, max_length=100, null=True)),
                ('token', models.TextField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'service_tokens',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Token',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('pid', models.CharField(max_length=50)),
                ('access_token', models.CharField(blank=True, max_length=255, null=True)),
                ('refresh_token', models.CharField(blank=True, max_length=255, null=True)),
                ('access_expires_at', models.DateTimeField(blank=True, null=True)),
                ('refresh_expires_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'tokens',
                'managed': False,
            },
        ),
    ]
