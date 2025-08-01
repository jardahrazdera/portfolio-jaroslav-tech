# Generated by Django 5.2.4 on 2025-07-20 13:02

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('coming_soon_mode', models.BooleanField(default=False, help_text="If checked, visitors will see the 'Coming Soon' overlay instead of the main site content.", verbose_name="Activate 'Coming Soon' Mode")),
            ],
            options={
                'verbose_name': 'Site Setting',
                'verbose_name_plural': 'Site Settings',
            },
        ),
    ]
