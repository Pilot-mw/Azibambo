from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_expense_is_paid_expense_payment_status_expense_purchase'),
        ('suppliers', '0003_add_warehouse_unit_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchase',
            name='linked_expense',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchase_loans', to='expenses.expense'),
        ),
        migrations.AddField(
            model_name='purchase',
            name='payment_status',
            field=models.CharField(choices=[('paid', 'PAID'), ('partial', 'PARTIAL / CREDIT'), ('unpaid', 'UNPAID')], default='unpaid', editable=False, max_length=20),
        ),
        migrations.AddField(
            model_name='purchase',
            name='remaining_amount',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12),
        ),
        migrations.AlterField(
            model_name='purchase',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, editable=False, help_text='Auto-calculated: unit_price × quantity', max_digits=12),
        ),
    ]
