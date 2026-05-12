from django.db import migrations


def backfill_conversion_fields(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    for product in Product.objects.all():
        unit_type = product.unit_type
        if unit_type == 'wine_glass':
            product.purchase_unit = 'Container'
            product.conversion_rate = product.glasses_per_liter or 28
        elif unit_type == 'Crate':
            product.purchase_unit = 'Crate'
            product.conversion_rate = product.crate_size or 20
        elif unit_type == 'Pack':
            product.purchase_unit = 'Pack'
            product.conversion_rate = product.pack_size or 6
        elif unit_type == 'Bottle':
            product.purchase_unit = 'Bottle'
            product.conversion_rate = product.shots_per_bottle or 1
        else:
            product.purchase_unit = 'Bottle'
            product.conversion_rate = 1
        product.save()


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0020_add_purchase_unit_conversion_rate'),
    ]

    operations = [
        migrations.RunPython(backfill_conversion_fields, migrations.RunPython.noop),
    ]
