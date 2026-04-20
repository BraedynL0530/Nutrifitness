from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_fix_dailylog_date_localdate'),
    ]

    operations = [
        migrations.AddField(
            model_name='fooditem',
            name='portion_size',
            field=models.FloatField(default=100.0),
        ),
        migrations.AddField(
            model_name='fooditem',
            name='unit',
            field=models.CharField(default='g', max_length=20),
        ),
    ]
