from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0019_fix_wine_glass_conversion_factor'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='purchase_unit',
            field=models.CharField(blank=True, choices=[('Crate', 'Crate'), ('Pack', 'Pack'), ('Bottle', 'Bottle'), ('Container', 'Container')], help_text='Warehouse receiving unit (overrides auto-detection)', max_length=20),
        ),
        migrations.AddField(
            model_name='product',
            name='conversion_rate',
            field=models.PositiveIntegerField(blank=True, help_text='1 purchase_unit = conversion_rate selling_units (overrides auto-detection)', null=True),
        ),
    ]
