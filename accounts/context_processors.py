import django.db.models as models
from .models import ActivityLog
from inventory.models import Product

def notification_count(request):
    if request.user.is_authenticated:
        low_stock_count = Product.objects.filter(
            quantity__lte=models.F('reorder_level')
        ).count()
    else:
        low_stock_count = 0
    return {
        'low_stock_count': low_stock_count,
        'unread_notifications': low_stock_count,
    }
