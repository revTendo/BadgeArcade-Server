from django.db import migrations, models

def copy_category_to_m2m(apps, schema_editor):
    """Copy each Title's existing single category (preserved as _old_category_id)
    into the new M2M table so nothing is lost."""
    Title = apps.get_model("shopdeckdb", "Title")
    through = Title.category.through
    rows = []
    for t in Title.objects.all():
        old_id = getattr(t, "_old_category_id", None)
        if old_id:
            rows.append(through(title_id=t.id, category_id=old_id))
    if rows:
        through.objects.bulk_create(rows, ignore_conflicts=True)

def reverse_m2m_to_category(apps, schema_editor):
    Title = apps.get_model("shopdeckdb", "Title")
    for t in Title.objects.all():
        first = t.category.first()
        if first:
            t._old_category_id = first.id
            t.save(update_fields=["_old_category_id"])

class Migration(migrations.Migration):

    dependencies = [
        ("shopdeckdb", "0020_bigint_size"),
    ]

    operations = [
        migrations.RenameField(
            model_name="title",
            old_name="category",
            new_name="_old_category",
        ),
        migrations.AddField(
            model_name="title",
            name="category",
            field=models.ManyToManyField(blank=True, to="shopdeckdb.category"),
        ),
        migrations.RunPython(copy_category_to_m2m, reverse_m2m_to_category),
        migrations.RemoveField(
            model_name="title",
            name="_old_category",
        ),
    ]
