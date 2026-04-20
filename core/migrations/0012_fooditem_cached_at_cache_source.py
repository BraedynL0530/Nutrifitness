from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_fooditem_portion_size_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='fooditem',
            name='cached_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='fooditem',
            name='cache_source',
            field=models.CharField(
                choices=[
                    ('local', 'Local'),
                    ('nutritionix', 'Nutritionix'),
                    ('off', 'Open Food Facts'),
                    ('manual', 'Manual'),
                ],
                default='manual',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='fooditem',
            name='barcode',
            field=models.CharField(blank=True, db_index=True, max_length=50, null=True, unique=True),
        ),
    ]
