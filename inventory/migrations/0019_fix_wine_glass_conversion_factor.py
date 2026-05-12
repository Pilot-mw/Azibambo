from django.db import migrations


def fix_wine_glasses(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    for product in Product.objects.filter(unit_type='wine_glass'):
        if product.bottle_quantity > 0:
            product.bottle_quantity = product.bottle_quantity // 5
        if product.quantity > 0:
            product.quantity = product.quantity // 5
        product.save()


def reverse_fix(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    for product in Product.objects.filter(unit_type='wine_glass'):
        if product.bottle_quantity > 0:
            product.bottle_quantity = product.bottle_quantity * 5
        if product.quantity > 0:
            product.quantity = product.quantity * 5
        product.save()


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0018_convert_drostody_hof_to_wine_glass'),
    ]

    operations = [
        migrations.RunPython(fix_wine_glasses, reverse_fix),
    ]
