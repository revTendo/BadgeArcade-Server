import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("shopdeckdb", "0014_title_genre_m2m"),
    ]

    operations = [
        migrations.CreateModel(
            name="parentalControl",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("parental_system_name", models.CharField(max_length=50, verbose_name="Rating system (e.g. ESRB, PEGI)")),
                ("parental_system_id", models.IntegerField(default=0)),
                ("age_name", models.CharField(max_length=50, verbose_name="Rating label (e.g. Everyone, Teen)")),
                ("age_number", models.IntegerField(default=0, verbose_name="Minimum age")),
                ("icon_url_normal", models.TextField(blank=True, default="")),
                ("icon_url_small", models.TextField(blank=True, default="")),
            ],
        ),
        migrations.AddField(
            model_name="title",
            name="parentalControl",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="shopdeckdb.parentalcontrol",
            ),
        ),
    ]
