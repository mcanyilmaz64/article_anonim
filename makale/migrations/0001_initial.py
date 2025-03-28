# Generated by Django 5.1.7 on 2025-03-25 08:46

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Makale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('takip_numarasi', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('eposta', models.EmailField(max_length=254)),
                ('dosya', models.FileField(upload_to='makaleler/')),
                ('yuklenme_tarihi', models.DateTimeField(auto_now_add=True)),
                ('revize_dosya', models.FileField(blank=True, null=True, upload_to='revizeler/')),
                ('durum', models.CharField(default='Yüklendi', max_length=50)),
            ],
        ),
    ]
