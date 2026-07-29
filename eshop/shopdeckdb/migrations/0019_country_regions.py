import django.db.models.deletion
from django.db import migrations, models

EU_COUNTRIES = [
    ("AT", "Austria"), ("BE", "Belgium"), ("BG", "Bulgaria"), ("HR", "Croatia"),
    ("CY", "Cyprus"), ("CZ", "Czechia"), ("DK", "Denmark"), ("EE", "Estonia"),
    ("FI", "Finland"), ("FR", "France"), ("DE", "Germany"), ("GR", "Greece"),
    ("HU", "Hungary"), ("IE", "Ireland"), ("IT", "Italy"), ("LV", "Latvia"),
    ("LT", "Lithuania"), ("LU", "Luxembourg"), ("MT", "Malta"), ("NL", "Netherlands"),
    ("PL", "Poland"), ("PT", "Portugal"), ("RO", "Romania"), ("SK", "Slovakia"),
    ("SI", "Slovenia"), ("ES", "Spain"), ("SE", "Sweden"), ("GB", "United Kingdom"),
    ("CH", "Switzerland"), ("NO", "Norway"), ("RU", "Russia"), ("ZA", "South Africa"),
    ("AU", "Australia"), ("NZ", "New Zealand"),
]

US_COUNTRIES = [
    ("US", "United States"), ("CA", "Canada"), ("MX", "Mexico"), ("BR", "Brazil"),
    ("AR", "Argentina"), ("CL", "Chile"), ("CO", "Colombia"), ("PE", "Peru"),
    ("VE", "Venezuela"), ("UY", "Uruguay"), ("PY", "Paraguay"), ("BO", "Bolivia"),
    ("EC", "Ecuador"), ("GT", "Guatemala"), ("CR", "Costa Rica"), ("PA", "Panama"),
    ("DO", "Dominican Republic"), ("TT", "Trinidad and Tobago"), ("JM", "Jamaica"),
    ("BS", "Bahamas"), ("BB", "Barbados"),
]

JP_COUNTRIES = [
    ("JP", "Japan"),
]

def seed_regions(apps, schema_editor):
    regionGroup = apps.get_model("shopdeckdb", "regionGroup")
    countryCode = apps.get_model("shopdeckdb", "countryCode")
    groups = {
        "EU": ("Europe", EU_COUNTRIES),
        "US": ("Americas", US_COUNTRIES),
        "JP": ("Japan", JP_COUNTRIES),
    }
    for code, (name, countries) in groups.items():
        grp, _ = regionGroup.objects.get_or_create(code=code, defaults={"name": name})
        for ccode, cname in countries:
            countryCode.objects.get_or_create(code=ccode, group=grp, defaults={"name": cname})

def unseed_regions(apps, schema_editor):
    apps.get_model("shopdeckdb", "countryCode").objects.all().delete()
    apps.get_model("shopdeckdb", "regionGroup").objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ("shopdeckdb", "0018_descriptors_sale_screenshots"),
    ]

    operations = [
        migrations.CreateModel(
            name="regionGroup",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=8, unique=True, help_text="EU, US, JP")),
                ("name", models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name="countryCode",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("code", models.CharField(help_text="ISO country code e.g. IT, FR, US", max_length=3)),
                ("name", models.CharField(blank=True, default="", max_length=100)),
                ("group", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="countries", to="shopdeckdb.regiongroup")),
            ],
        ),
        migrations.AddField(
            model_name="title",
            name="countries",
            field=models.ManyToManyField(blank=True, help_text="Countries this title is available in. Empty = hidden everywhere.", to="shopdeckdb.countrycode"),
        ),
        migrations.AddField(
            model_name="category",
            name="countries",
            field=models.ManyToManyField(blank=True, help_text="Countries this category appears in. Empty = hidden everywhere.", to="shopdeckdb.countrycode"),
        ),
        migrations.RunPython(seed_regions, unseed_regions),
    ]
