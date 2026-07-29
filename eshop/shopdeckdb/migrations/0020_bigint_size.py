from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("shopdeckdb", "0019_country_regions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="title",
            name="size",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="titlecontentsize",
            name="tmd_size",
            field=models.BigIntegerField(default=0),
        ),
    ]
