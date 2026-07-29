

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('shopdeckdb', '0003_remove_title_ticket_remove_title_ticket_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='client3ds',
            name='devicecert_consoldeid',
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
    ]
