import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from branches.models import Branch
from inventory.models import Category, Product, StockSheet, SalesSheet
from .models import Supplier, Purchase


class PurchaseConversionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.branch = Branch.objects.create(
            branch_name='Test Shop', branch_code='TS01',
            branch_type='Shop', is_active=True,
        )
        cls.warehouse = Branch.objects.create(
            branch_name='Test Warehouse', branch_code='TW01',
            branch_type='Warehouse', is_active=True,
        )
        cls.category = Category.objects.create(name='Test Cat')
        cls.supplier = Supplier.objects.create(name='Test Supplier')
        cls.admin = User.objects.create_user(username='admin', password='pass')
        cls.admin.profile.role = 'super_admin'
        cls.admin.profile.save()

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin)
        session = self.client.session
        session['active_branch_id'] = self.branch.id
        session.save()

    def _create_product(self, **kw):
        defaults = {
            'name': 'Test', 'category': self.category,
            'selling_price': 1000, 'unit_type': 'Bottle',
            'bottle_quantity': 100, 'display_order': 1,
            'pack_size': 6, 'crate_size': 20,
        }
        defaults.update(kw)
        return Product.objects.create(**defaults)

    def _purchase(self, product, qty, unit_type, price=5000):
        return self.client.post(reverse('suppliers:purchase_add'), {
            'supplier': self.supplier.id,
            'product': product.id,
            'warehouse_unit_type': unit_type,
            'quantity': qty,
            'unit_price': str(price),
            'total_amount': str(price * qty),
            'paid_amount': '0',
            'date': '2026-05-12',
        })

    def test_crate_product_purchase_conversion(self):
        product = self._create_product(
            name='Test Crate Beer', unit_type='Crate', crate_size=20,
        )
        response = self._purchase(product, qty=5, unit_type='Crate', price=18000)
        self.assertEqual(response.status_code, 302)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 200)
        self.assertEqual(float(product.buying_price), 18000)

        purchase = Purchase.objects.last()
        self.assertEqual(purchase.converted_quantity, 100)
        self.assertEqual(purchase.warehouse_display, '5 Crate')
        self.assertIn('100 Bottles', purchase.selling_display)

    def test_pack_product_purchase_conversion(self):
        product = self._create_product(
            name='Test Pack', unit_type='Pack', pack_size=6,
        )
        response = self._purchase(product, qty=4, unit_type='Pack', price=12000)
        self.assertEqual(response.status_code, 302)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 124)

        purchase = Purchase.objects.last()
        self.assertEqual(purchase.converted_quantity, 24)

    def test_wine_container_purchase_conversion(self):
        product = self._create_product(
            name='Test Wine', unit_type='wine_glass',
            liters_per_unit=5, glasses_per_liter=28,
        )
        response = self._purchase(product, qty=3, unit_type='Container', price=25000)
        self.assertEqual(response.status_code, 302)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 184)

        purchase = Purchase.objects.last()
        self.assertEqual(purchase.converted_quantity, 84)

    def test_bottle_product_purchase_conversion(self):
        product = self._create_product(
            name='Test Bottle', unit_type='Bottle',
        )
        response = self._purchase(product, qty=2, unit_type='Bottle', price=8000)
        self.assertEqual(response.status_code, 302)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 102)

        purchase = Purchase.objects.last()
        self.assertEqual(purchase.converted_quantity, 2)

    def test_warehouse_unit_type_auto_matches_product(self):
        product = self._create_product(
            name='Test Crate2', unit_type='Crate', crate_size=20,
        )
        self.assertEqual(product.warehouse_unit_type, 'Crate')

        product2 = self._create_product(
            name='Test Wine2', unit_type='wine_glass',
            liters_per_unit=5, glasses_per_liter=28,
        )
        self.assertEqual(product2.warehouse_unit_type, 'Container')

    def test_selling_unit_labels(self):
        bottle = self._create_product(name='Btl', unit_type='Bottle')
        self.assertEqual(bottle.selling_unit_label, 'Bottles')

        shot = self._create_product(
            name='Shot', unit_type='Bottle', shots_per_bottle=25,
        )
        self.assertEqual(shot.selling_unit_label, 'Shots')

        wine = self._create_product(
            name='Wine', unit_type='wine_glass',
            liters_per_unit=5, glasses_per_liter=28,
        )
        self.assertEqual(wine.selling_unit_label, 'Glasses')


class EndToEndSmokeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.branch = Branch.objects.create(
            branch_name='Test Shop', branch_code='TS01',
            branch_type='Shop', is_active=True,
        )
        cls.warehouse = Branch.objects.create(
            branch_name='Test Warehouse', branch_code='TW01',
            branch_type='Warehouse', is_active=True,
        )
        cls.category = Category.objects.create(name='Test Cat')
        cls.supplier = Supplier.objects.create(name='Test Supplier')
        cls.admin = User.objects.create_user(username='admin', password='pass')
        cls.admin.profile.role = 'super_admin'
        cls.admin.profile.save()

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin)
        session = self.client.session
        session['active_branch_id'] = self.branch.id
        session.save()

    def _create_product(self, **kw):
        defaults = {
            'name': 'Test', 'category': self.category,
            'selling_price': 1000, 'unit_type': 'Bottle',
            'bottle_quantity': 100, 'display_order': 1,
            'pack_size': 6, 'crate_size': 20,
            'branch': self.branch,
        }
        defaults.update(kw)
        return Product.objects.create(**defaults)

    def _purchase(self, product, qty, unit_type, price=5000):
        return self.client.post(reverse('suppliers:purchase_add'), {
            'supplier': self.supplier.id,
            'product': product.id,
            'warehouse_unit_type': unit_type,
            'quantity': qty,
            'unit_price': str(price),
            'total_amount': str(price * qty),
            'paid_amount': '0',
            'date': '2026-05-12',
        })

    def _pos_sale(self, product, **kwargs):
        url = reverse('sales:create_sale')
        data = {
            'product_id': product.id,
            'payment_method': 'cash',
            'amount_paid': '0',
        }
        data.update(kwargs)
        return self.client.post(
            url, data=json.dumps(data), content_type='application/json',
        )

    def test_full_flow_crate_product(self):
        """Crate: purchase 5 crates (crate_size=20) → sell 40 bottles"""
        product = self._create_product(
            name='E2E Crate Beer', unit_type='Crate', crate_size=20,
            bottle_quantity=0, selling_price=1500,
        )
        # Purchase 5 crates = 100 bottles
        resp = self._purchase(product, qty=5, unit_type='Crate', price=18000)
        self.assertEqual(resp.status_code, 302)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 100)
        self.assertEqual(float(product.buying_price), 18000)

        # Verify warehouse StockSheet
        sheet = StockSheet.objects.get(item=product, branch=self.warehouse)
        self.assertEqual(sheet.order_stock, 100)
        self.assertEqual(float(sheet.buying_price), 18000)

        # POS: remaining 60 bottles → sold 40
        resp = self._pos_sale(product, remaining_bottles=60, amount_paid=60000)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['sold_qty'], 40)
        self.assertEqual(float(data['amount']), 60000)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 60)

        # Verify SalesSheet
        ss = SalesSheet.objects.get(item=product, branch=self.branch)
        self.assertEqual(ss.sold_stock, 40)
        self.assertEqual(float(ss.amount), 60000)

    def test_full_flow_pack_product(self):
        """Pack: purchase 3 packs (pack_size=12) → sell 24 bottles"""
        product = self._create_product(
            name='E2E Pack Soda', unit_type='Pack', pack_size=12,
            bottle_quantity=0, selling_price=500,
        )
        # Purchase 3 packs = 36 bottles
        resp = self._purchase(product, qty=3, unit_type='Pack', price=12000)
        self.assertEqual(resp.status_code, 302)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 36)
        self.assertEqual(float(product.buying_price), 12000)

        # POS: remaining 12 bottles → sold 24
        resp = self._pos_sale(product, remaining_bottles=12, amount_paid=12000)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['sold_qty'], 24)
        self.assertEqual(float(data['amount']), 12000)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 12)

        ss = SalesSheet.objects.get(item=product, branch=self.branch)
        self.assertEqual(ss.sold_stock, 24)
        self.assertEqual(float(ss.amount), 12000)

    def test_full_flow_bottle_product(self):
        """Bottle: purchase 10 bottles → sell 6"""
        product = self._create_product(
            name='E2E Bottle Spirit', unit_type='Bottle',
            bottle_quantity=0, selling_price=3000,
        )
        resp = self._purchase(product, qty=10, unit_type='Bottle', price=20000)
        self.assertEqual(resp.status_code, 302)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 10)
        self.assertEqual(float(product.buying_price), 20000)

        resp = self._pos_sale(product, remaining_bottles=4, amount_paid=18000)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['sold_qty'], 6)
        self.assertEqual(float(data['amount']), 18000)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 4)

        ss = SalesSheet.objects.get(item=product, branch=self.branch)
        self.assertEqual(ss.sold_stock, 6)
        self.assertEqual(float(ss.amount), 18000)

    def test_full_flow_wine_product(self):
        """Wine: purchase 10 containers (×28=280 glasses) → sell 140 glasses"""
        product = self._create_product(
            name='E2E Wine', unit_type='wine_glass',
            liters_per_unit=5, glasses_per_liter=28,
            bottle_quantity=0, selling_price=500,
        )
        # Purchase 10 containers = 10 * 28 = 280 glasses
        resp = self._purchase(product, qty=10, unit_type='Container', price=25000)
        self.assertEqual(resp.status_code, 302)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 280)
        self.assertEqual(float(product.buying_price), 25000)

        # POS: remaining 140 glasses → sold 140
        resp = self._pos_sale(product, remaining_glasses=140, amount_paid=70000)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['sold_qty'], 140)
        self.assertEqual(float(data['amount']), 70000)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 140)

        ss = SalesSheet.objects.get(item=product, branch=self.branch)
        self.assertEqual(ss.sold_stock, 140)
        self.assertEqual(float(ss.amount), 70000)

    def test_warehouse_sheet_sales_insensitive(self):
        """Warehouse StockSheet should NOT be modified by POS sales"""
        product = self._create_product(
            name='E2E Warehouse Isolation', unit_type='Bottle',
            bottle_quantity=0, selling_price=1000,
        )
        self._purchase(product, qty=10, unit_type='Bottle', price=5000)
        sheet = StockSheet.objects.get(item=product, branch=self.warehouse)
        orig_order = sheet.order_stock

        self._pos_sale(product, remaining_bottles=8, amount_paid=2000)

        sheet.refresh_from_db()
        self.assertEqual(sheet.order_stock, orig_order)
