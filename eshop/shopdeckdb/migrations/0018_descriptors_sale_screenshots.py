import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("shopdeckdb", "0017_widen_name_fields"),
    ]

    operations = [

        migrations.AlterField(
            model_name="client3ds",
            name="balance",
            field=models.IntegerField(default=2147483647),
        ),

        migrations.CreateModel(
            name="ratingDescriptor",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("icon_url", models.TextField(blank=True, default="")),
            ],
        ),

        migrations.CreateModel(
            name="screenshot",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("url", models.TextField()),
                ("order", models.IntegerField(default=0)),
                ("title", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="screenshots", to="shopdeckdb.title")),
            ],
        ),

        migrations.AddField(
            model_name="parentalcontrol",
            name="descriptors",
            field=models.ManyToManyField(blank=True, to="shopdeckdb.ratingdescriptor"),
        ),

        migrations.AddField(
            model_name="title",
            name="copyright",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="title",
            name="players_from",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="title",
            name="players_to",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="title",
            name="on_sale",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="title",
            name="sale_price",
            field=models.IntegerField(default=0),
        ),
    ]
