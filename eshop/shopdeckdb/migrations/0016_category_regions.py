from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("shopdeckdb", "0015_parentalcontrol"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="regions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Regions this category appears in. Leave empty to show in ALL regions.",
                to="shopdeckdb.region",
            ),
        ),
    ]
