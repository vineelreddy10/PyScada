# Generated by Django 3.2 on 2023-02-01 12:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyscada', '0098_alter_device_polling_interval'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dictionaryitem',
            name='label',
            field=models.CharField(blank=True, default='', max_length=400),
        ),
    ]