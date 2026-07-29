

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('shopdeckdb', '0006_alter_client3ds_devicecert_consoleid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client3ds',
            name='uniquekey',
            field=models.CharField(max_length=21),
        ),
    ]
