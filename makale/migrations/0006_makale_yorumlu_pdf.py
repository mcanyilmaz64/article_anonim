# Generated by Django 5.1.7 on 2025-03-26 11:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('makale', '0005_makale_keywords'),
    ]

    operations = [
        migrations.AddField(
            model_name='makale',
            name='yorumlu_pdf',
            field=models.FileField(blank=True, null=True, upload_to='yorumlu/'),
        ),
    ]
