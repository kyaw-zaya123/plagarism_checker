# Generated by Django 5.0.8 on 2025-02-19 20:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filecompare', '0012_remove_comparison_name_of_comparison_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comparison',
            name='similarity_category',
        ),
    ]
