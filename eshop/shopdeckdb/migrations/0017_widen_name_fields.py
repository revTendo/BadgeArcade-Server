from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("shopdeckdb", "0016_category_regions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="title",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="title",
            name="product_code",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="category",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="region",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="region",
            name="initial",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AlterField(
            model_name="genre",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="platform",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="publisher",
            name="publisher_name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="movie",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="searchcategory",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="announcement",
            name="title",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="parentalcontrol",
            name="parental_system_name",
            field=models.CharField(max_length=200, verbose_name="Rating system (e.g. ESRB, PEGI)"),
        ),
        migrations.AlterField(
            model_name="parentalcontrol",
            name="age_name",
            field=models.CharField(max_length=200, verbose_name="Rating label (e.g. Everyone, Teen)"),
        ),
        migrations.AlterField(
            model_name="dlccontenttitle",
            name="name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AlterField(
            model_name="dlccontentsetattribute",
            name="name",
            field=models.CharField(max_length=200),
        ),
    ]
