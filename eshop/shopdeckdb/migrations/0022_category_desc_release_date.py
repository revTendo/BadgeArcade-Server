from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("shopdeckdb", "0021_title_category_m2m"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="description",
            field=models.TextField(blank=True, default="", help_text="Optional description shown for this category."),
        ),
        migrations.AddField(
            model_name="title",
            name="release_date",
            field=models.DateField(blank=True, null=True, help_text="The title's release date (editable)."),
        ),
    ]
