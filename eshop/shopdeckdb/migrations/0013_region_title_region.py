

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('shopdeckdb', '0012_alter_announcement_id_alter_category_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='region',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
                ('initial', models.CharField(blank=True, default='', max_length=8)),
            ],
        ),
        migrations.AddField(
            model_name='title',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='shopdeckdb.region'),
        ),
    ]
