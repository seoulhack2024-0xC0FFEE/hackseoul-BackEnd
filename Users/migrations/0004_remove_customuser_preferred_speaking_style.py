# Generated by Django 5.0.7 on 2024-08-25 06:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Users', '0003_customuser_preferred_speaking_style'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='preferred_speaking_style',
        ),
    ]
