from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0003_add_warehouse_unit_type'),
        ('expenses', '0002_expense_branch'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='is_paid',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='expense',
            name='payment_status',
            field=models.CharField(choices=[('unpaid', 'Unpaid'), ('paid', 'Paid')], default='unpaid', max_length=20),
        ),
        migrations.AddField(
            model_name='expense',
            name='purchase',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expense_loans', to='suppliers.purchase'),
        ),
    ]
