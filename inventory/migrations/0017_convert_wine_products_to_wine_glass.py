from django.db import migrations

WINE_NAMES = [
    'Roses', 'Overmeer White', 'Overmeer Red', 'Overmeer Harvest',
    '4th Street', 'Namaqua', 'Cellar Cask', 'Drostdy Hof',
]


def convert_wine_to_glasses(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    for name in WINE_NAMES:
        try:
            product = Product.objects.get(name=name)
        except Product.DoesNotExist:
            continue
        liters_per_unit = 5
        glasses_per_liter = 28
        total_glasses = product.bottle_quantity * liters_per_unit * glasses_per_liter
        product.unit_type = 'wine_glass'
        product.liters_per_unit = liters_per_unit
        product.glasses_per_liter = glasses_per_liter
        product.bottle_quantity = total_glasses
        product.pack_quantity = 0
        product.crate_quantity = 0
        product.shot_quantity = 0
        product.quantity = total_glasses
        product.save()


def reverse_to_piece(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    for name in WINE_NAMES:
        try:
            product = Product.objects.get(name=name)
        except Product.DoesNotExist:
            continue
        units = product.bottle_quantity // (product.liters_per_unit * product.glasses_per_liter) if product.liters_per_unit and product.glasses_per_liter else 0
        product.unit_type = 'Piece'
        product.bottle_quantity = units
        product.quantity = units
        product.save()


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0016_add_wine_glass_fields'),
    ]

    operations = [
        migrations.RunPython(convert_wine_to_glasses, reverse_to_piece),
    ]
