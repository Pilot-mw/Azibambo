from django.db import migrations


PET_PRODUCTS = ['CocaCola Pet', 'Fanta Pet', 'Sprite Pet']
PACK_SIZE = 12
CRATE_SIZE = 20


def convert_to_pack(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    for name in PET_PRODUCTS:
        try:
            product = Product.objects.get(name=name)
        except Product.DoesNotExist:
            continue
        total_bottles = product.bottle_quantity + product.crate_quantity * CRATE_SIZE
        packs = total_bottles // PACK_SIZE
        remaining_bottles = total_bottles % PACK_SIZE
        product.unit_type = 'Pack'
        product.pack_size = PACK_SIZE
        product.units_per_pack = PACK_SIZE
        product.pack_quantity = packs
        product.bottle_quantity = remaining_bottles
        product.crate_quantity = 0
        product.save()


def reverse_to_crate(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    for name in PET_PRODUCTS:
        try:
            product = Product.objects.get(name=name)
        except Product.DoesNotExist:
            continue
        total_bottles = product.pack_quantity * product.pack_size + product.bottle_quantity
        crates = total_bottles // CRATE_SIZE
        remaining_bottles = total_bottles % CRATE_SIZE
        product.unit_type = 'Crate'
        product.pack_size = 12
        product.units_per_pack = 6
        product.crate_quantity = crates
        product.bottle_quantity = remaining_bottles
        product.pack_quantity = 0
        product.save()


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0014_convert_spirits_750ml_to_bottle'),
    ]

    operations = [
        migrations.RunPython(convert_to_pack, reverse_to_crate),
    ]
