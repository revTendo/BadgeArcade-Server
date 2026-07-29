

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('shopdeckdb', '0009_alter_item_limit_ownedticket'),
    ]

    operations = [
        migrations.AddField(
            model_name='title',
            name='demo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='shopdeckdb.title'),
        ),
    ]
