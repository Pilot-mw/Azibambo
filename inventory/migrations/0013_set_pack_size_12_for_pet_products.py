from django.db import migrations


def set_pack_size_12(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    Product.objects.filter(name__in=[
        'CocaCola Pet', 'Fanta Pet', 'Sprite Pet', 'Sobo Ginger',
    ]).update(pack_size=12)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0012_product_crate_size_product_pack_size'),
    ]

    operations = [
        migrations.RunPython(set_pack_size_12),
    ]
