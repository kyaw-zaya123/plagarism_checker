# Generated by Django 5.0.8 on 2025-02-08 12:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filecompare', '0002_file_comparison_delete_comparisonhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='comparison',
            name='similarity_category',
            field=models.CharField(blank=True, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], max_length=10, null=True),
        ),
    ]
