# Generated by Django 5.0.8 on 2025-02-19 19:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filecompare', '0011_remove_comparison_session_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comparison',
            name='name_of_comparison',
        ),
        migrations.AddField(
            model_name='comparison',
            name='comparison_name',
            field=models.CharField(default='Unnamed Comparison', max_length=200),
        ),
    ]
