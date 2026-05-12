from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Sale, SaleItem
from inventory.models import SalesSheet
from inventory.services.conversion_engine import convert_purchase_to_base


def _get_base_quantity(item):
    product = item.product
    if not product:
        return item.quantity
    qty = item.quantity
    unit = item.selling_unit
    if unit in ('Bottle', 'Shot', 'Glass'):
        return qty
    elif unit in ('Crate', 'Pack'):
        return convert_purchase_to_base(qty, product)
    return qty


def _sync_saleitem_to_sheet(item, multiplier=1):
    product = item.product
    if not product:
        return
    sale = item.sale
    base_qty = _get_base_quantity(item)
    delta = base_qty * multiplier
    sale_date = sale.created_at.date()

    sheet, created = SalesSheet.objects.get_or_create(
        item=product,
        date=sale_date,
        branch=sale.branch,
        defaults={
            'category': product.category,
            'open_stock': 0,
            'add_stock': 0,
            'selling_price': product.selling_price,
            'sold_stock': max(0, delta),
            'created_by': sale.cashier,
        },
    )
    if not created:
        sheet.sold_stock = max(0, sheet.sold_stock + delta)
        sheet.selling_price = product.selling_price
        sheet.save()


def _sync_sale_to_sheet(sale, multiplier=1):
    for item in sale.items.select_related('product').all():
        _sync_saleitem_to_sheet(item, multiplier)


@receiver(post_save, sender=SaleItem)
def sync_saleitem_to_salessheet(sender, instance, created, **kwargs):
    if created and instance.sale.status == 'completed':
        _sync_saleitem_to_sheet(instance, multiplier=1)


@receiver(post_save, sender=Sale)
def sync_refund_to_salessheet(sender, instance, **kwargs):
    if instance.status not in ('refunded', 'cancelled'):
        return
    if kwargs.get('created', False):
        return
    try:
        old = Sale.objects.only('status').get(pk=instance.pk)
        if old.status == instance.status:
            return
        if old.status == 'completed':
            _sync_sale_to_sheet(instance, multiplier=-1)
    except Sale.DoesNotExist:
        return
