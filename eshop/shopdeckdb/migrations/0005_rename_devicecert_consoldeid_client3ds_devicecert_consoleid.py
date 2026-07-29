

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('shopdeckdb', '0004_client3ds_devicecert_consoldeid'),
    ]

    operations = [
        migrations.RenameField(
            model_name='client3ds',
            old_name='devicecert_consoldeid',
            new_name='devicecert_consoleid',
        ),
    ]
