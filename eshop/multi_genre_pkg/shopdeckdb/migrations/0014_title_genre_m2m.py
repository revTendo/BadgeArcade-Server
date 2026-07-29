from django.db import migrations, models

def copy_genre_to_m2m(apps, schema_editor):
    """Copy each Title's existing single genre (old genre_id column, preserved as
    _old_genre_id) into the new M2M table so nothing is lost."""
    Title = apps.get_model("shopdeckdb", "Title")
    through = Title.genre.through
    rows = []
    for t in Title.objects.all():
        old_id = getattr(t, "_old_genre_id", None)
        if old_id:
            rows.append(through(title_id=t.id, genre_id=old_id))
    if rows:
        through.objects.bulk_create(rows, ignore_conflicts=True)

def reverse_m2m_to_genre(apps, schema_editor):
    """Reverse: put the first M2M genre back into the old single column."""
    Title = apps.get_model("shopdeckdb", "Title")
    for t in Title.objects.all():
        first = t.genre.first()
        if first:
            t._old_genre_id = first.id
            t.save(update_fields=["_old_genre_id"])

class Migration(migrations.Migration):

    dependencies = [
        ("shopdeckdb", "0013_region_title_region"),
    ]

    operations = [

        migrations.RenameField(
            model_name="title",
            old_name="genre",
            new_name="_old_genre",
        ),

        migrations.AddField(
            model_name="title",
            name="genre",
            field=models.ManyToManyField(to="shopdeckdb.genre"),
        ),

        migrations.RunPython(copy_genre_to_m2m, reverse_m2m_to_genre),

        migrations.RemoveField(
            model_name="title",
            name="_old_genre",
        ),
    ]
