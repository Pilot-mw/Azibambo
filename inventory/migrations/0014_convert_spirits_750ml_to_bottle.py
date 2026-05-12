from django.db import migrations


def convert_spirits_750ml_to_bottle(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    ProductCrateSize = apps.get_model('inventory', 'Product')

    updates = {
        'Malawi Gin 750ML': {'name': 'Malawi Gin 750ML', 'crate_size': 20},
        'Premier Brandy 750ML': {'name': 'Premier Brandy 750ML', 'crate_size': 20},
        'Malawi Vodka 750ML': {'name': 'Malawi Vodka 750ML', 'crate_size': 20},
    }

    for name, info in updates.items():
        try:
            product = Product.objects.get(name=name)
            crate_size = info['crate_size']
            bottles_from_crates = product.crate_quantity * crate_size
            product.bottle_quantity = (product.bottle_quantity or 0) + bottles_from_crates
            product.crate_quantity = 0
            product.unit_type = 'Bottle'
            product.save()
        except Product.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0013_set_pack_size_12_for_pet_products'),
    ]

    operations = [
        migrations.RunPython(convert_spirits_750ml_to_bottle),
    ]
