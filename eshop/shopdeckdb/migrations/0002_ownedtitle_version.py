

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('shopdeckdb', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ownedtitle',
            name='version',
            field=models.IntegerField(default=1024),
            preserve_default=False,
        ),
    ]
