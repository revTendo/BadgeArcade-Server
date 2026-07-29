

import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('shopdeckdb', '0010_title_demo'),
    ]

    operations = [
        migrations.CreateModel(
            name='dlcContentSet',
            fields=[
                ('id', models.IntegerField(blank=True, primary_key=True, serialize=False)),
                ('order', models.IntegerField(default=0)),
                ('content_indexes', models.CharField(blank=True, default='', max_length=255, verbose_name='Content indexes (comma separated)')),
                ('itemcode', models.CharField(blank=True, default='', max_length=16)),
                ('item_id', models.IntegerField(blank=True, null=True)),
                ('price', models.CharField(blank=True, default='0', max_length=16)),
                ('currency', models.CharField(blank=True, default='CREDIT', max_length=8)),
            ],
        ),
        migrations.CreateModel(
            name='dlcContentTitle',
            fields=[
                ('id', models.IntegerField(blank=True, primary_key=True, serialize=False)),
                ('tid', models.CharField(max_length=16, verbose_name='DLC Title ID')),
                ('name', models.CharField(blank=True, default='', max_length=100)),
                ('paginated', models.BooleanField(default=False)),
                ('page_limit', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='titleContentSize',
            fields=[
                ('id', models.IntegerField(blank=True, primary_key=True, serialize=False)),
                ('app_tid', models.CharField(max_length=16, verbose_name='Application Title ID')),
                ('content_size', models.CharField(blank=True, default='', max_length=64)),
                ('tmd_size', models.IntegerField(default=0)),
                ('max_content_index', models.IntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name='item',
            name='content_index',
            field=models.CharField(blank=True, default='0', max_length=150),
        ),
        migrations.AddField(
            model_name='item',
            name='name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='item',
            name='nintendo_content_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='dlcContentSetAttribute',
            fields=[
                ('id', models.IntegerField(blank=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('value', models.TextField(blank=True, default='')),
                ('content_set', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attributes', to='shopdeckdb.dlccontentset')),
            ],
        ),
        migrations.AddField(
            model_name='dlccontentset',
            name='dlc',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='content_sets', to='shopdeckdb.dlccontenttitle'),
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('age', models.IntegerField()),
                ('gender', models.CharField(max_length=10)),
                ('q3', models.CharField(max_length=10)),
                ('q4', models.BooleanField()),
                ('q5', models.BooleanField()),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shopdeckdb.client3ds')),
                ('voted_title', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='shopdeckdb.title')),
            ],
        ),
    ]
