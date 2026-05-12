import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from branches.models import Branch
from inventory.models import Category, Product, SalesSheet
from accounts.models import Profile


class POSTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.branch = Branch.objects.create(
            branch_name='Test Shop',
            branch_code='TS01',
            branch_type='Shop',
            is_active=True,
        )
        cls.warehouse = Branch.objects.create(
            branch_name='Test Warehouse',
            branch_code='TW01',
            branch_type='Warehouse',
            is_active=True,
        )
        cls.category_beers = Category.objects.create(name='Beers & Softs')
        cls.category_spirits = Category.objects.create(name='Spirits & Others')

        cls.admin_user = User.objects.create_user(
            username='admin', password='adminpass'
        )
        cls.admin_user.profile.role = 'super_admin'
        cls.admin_user.profile.branch = cls.branch
        cls.admin_user.profile.save()

        cls.cashier_user = User.objects.create_user(
            username='cashier', password='cashierpass'
        )
        cls.cashier_user.profile.role = 'cashier'
        cls.cashier_user.profile.branch = cls.branch
        cls.cashier_user.profile.allowed_categories.add(cls.category_beers)
        cls.cashier_user.profile.save()

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin_user)
        # Simulate the branch middleware
        session = self.client.session
        session['active_branch_id'] = self.branch.id
        session.save()

    def _create_product(self, **kwargs):
        defaults = {
            'name': 'Test Product',
            'category': self.category_beers,
            'selling_price': 1000,
            'unit_type': 'Bottle',
            'bottle_quantity': 50,
            'pack_quantity': 0,
            'crate_quantity': 0,
            'shots_per_bottle': 1,
            'shot_quantity': 0,
            'pack_size': 6,
            'crate_size': 20,
            'display_order': 1,
            'branch': self.branch,
        }
        defaults.update(kwargs)
        return Product.objects.create(**defaults)

    def _post_sale(self, product, remaining_bottles, remaining_shots=0,
                   payment_method='cash', amount_paid=0):
        url = reverse('sales:create_sale')
        data = {
            'product_id': product.id,
            'remaining_bottles': remaining_bottles,
            'remaining_shots': remaining_shots,
            'payment_method': payment_method,
            'amount_paid': str(amount_paid),
        }
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
        )
        return response

    def test_bottle_product_sale_success(self):
        product = self._create_product(
            name='Test Beer',
            unit_type='Bottle',
            bottle_quantity=50,
        )
        response = self._post_sale(product, remaining_bottles=30, amount_paid=20000)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['sold_qty'], 20)
        self.assertEqual(data['amount'], 20000)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 30)
        self.assertEqual(product.pack_quantity, 0)
        self.assertEqual(product.crate_quantity, 0)

        sheet = SalesSheet.objects.get(item=product, branch=self.branch)
        self.assertEqual(sheet.sold_stock, 20)
        self.assertEqual(sheet.open_stock, 0)
        self.assertEqual(sheet.add_stock, 0)
        self.assertEqual(sheet.total_stock, 0)
        self.assertEqual(sheet.remaining_stock, -20)
        self.assertEqual(float(sheet.amount), 20000)

    def test_crate_product_sale_success(self):
        product = self._create_product(
            name='Test Crate Beer',
            unit_type='Crate',
            bottle_quantity=100,
            pack_quantity=0,
            crate_quantity=5,
            pack_size=6,
            crate_size=20,
        )
        response = self._post_sale(product, remaining_bottles=80, amount_paid=20000)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['sold_qty'], 120)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 80)
        self.assertEqual(product.pack_quantity, 0)
        self.assertEqual(product.crate_quantity, 0)

        sheet = SalesSheet.objects.get(item=product, branch=self.branch)
        self.assertEqual(sheet.sold_stock, 120)
        self.assertEqual(sheet.remaining_stock, -120)

    def test_pack_product_sale_success(self):
        product = self._create_product(
            name='Test Pack Beer',
            unit_type='Pack',
            bottle_quantity=36,
            pack_quantity=6,
            pack_size=6,
        )
        response = self._post_sale(product, remaining_bottles=24, amount_paid=12000)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['sold_qty'], 48)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 24)
        self.assertEqual(product.pack_quantity, 0)
        self.assertEqual(product.crate_quantity, 0)

    def test_shot_product_sale_success(self):
        product = self._create_product(
            name='Test Spirit',
            category=self.category_spirits,
            unit_type='Bottle',
            bottle_quantity=10,
            shots_per_bottle=21,
            shot_quantity=5,
            selling_price=21000,
        )
        total_base = 10 * 21 + 5
        response = self._post_sale(
            product, remaining_bottles=5, remaining_shots=10,
            amount_paid=50000,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        remaining_base = 5 * 21 + 10
        expected_sold = total_base - remaining_base
        self.assertEqual(data['sold_qty'], expected_sold)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 5)
        self.assertEqual(product.shot_quantity, 10)

    def test_remaining_exceeds_total_returns_error(self):
        product = self._create_product(bottle_quantity=10)
        response = self._post_sale(product, remaining_bottles=20)
        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot exceed', response.json()['error'])

    def test_negative_remaining_returns_error(self):
        product = self._create_product(bottle_quantity=10)
        response = self._post_sale(product, remaining_bottles=-1)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Negative', response.json()['error'])

    def test_zero_sold_returns_error(self):
        product = self._create_product(bottle_quantity=10)
        response = self._post_sale(product, remaining_bottles=10)
        self.assertEqual(response.status_code, 400)
        self.assertIn('No stock sold', response.json()['error'])

    def test_cashier_restricted_from_spirits(self):
        self.client.force_login(self.cashier_user)
        product = self._create_product(
            name='Restricted Spirit',
            category=self.category_spirits,
            bottle_quantity=10,
        )
        response = self._post_sale(product, remaining_bottles=5)
        self.assertEqual(response.status_code, 403)
        self.assertIn('not in your allowed categories', response.json()['error'])

    def test_cashier_allowed_for_beers(self):
        self.client.force_login(self.cashier_user)
        product = self._create_product(
            name='Allowed Beer',
            category=self.category_beers,
            bottle_quantity=10,
        )
        response = self._post_sale(product, remaining_bottles=5, amount_paid=5000)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_salesheet_auto_computes_correctly(self):
        product = self._create_product(bottle_quantity=100, selling_price=500)
        response = self._post_sale(product, remaining_bottles=70, amount_paid=15000)
        self.assertEqual(response.status_code, 200)

        sheet = SalesSheet.objects.get(item=product, branch=self.branch)
        self.assertEqual(sheet.open_stock, 0)
        self.assertEqual(sheet.add_stock, 0)
        self.assertEqual(sheet.total_stock, 0)
        self.assertEqual(sheet.sold_stock, 30)
        self.assertEqual(sheet.remaining_stock, -30)
        self.assertEqual(float(sheet.amount), 15000)

    def test_refund_restores_stock(self):
        product = self._create_product(bottle_quantity=50, selling_price=1000)
        response = self._post_sale(product, remaining_bottles=30, amount_paid=20000)
        self.assertEqual(response.status_code, 200)
        sale_id = response.json()['sale_id']
        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 30)

        from sales.models import Sale
        sale = Sale.objects.get(id=sale_id)
        self.client.post(reverse('sales:refund_sale', args=[sale_id]))

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 50)

    def test_branch_isolation(self):
        other_branch = Branch.objects.create(
            branch_name='Other Shop',
            branch_code='OS01',
            branch_type='Shop',
            is_active=True,
        )
        product = self._create_product(bottle_quantity=50)
        response = self._post_sale(product, remaining_bottles=30, amount_paid=20000)
        self.assertEqual(response.status_code, 200)

        sheets = SalesSheet.objects.filter(item=product, branch=other_branch)
        self.assertEqual(sheets.count(), 0)

        sheets = SalesSheet.objects.filter(item=product, branch=self.branch)
        self.assertEqual(sheets.count(), 1)

    def test_wine_glass_product_sale_success(self):
        product = self._create_product(
            name='Test Wine',
            unit_type='wine_glass',
            bottle_quantity=140,
            liters_per_unit=5,
            glasses_per_liter=28,
            selling_price=500,
        )
        url = reverse('sales:create_sale')
        data = {
            'product_id': product.id,
            'remaining_glasses': 130,
            'payment_method': 'cash',
            'amount_paid': '5000',
        }
        response = self.client.post(
            url, data=json.dumps(data), content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        resp_data = response.json()
        self.assertTrue(resp_data['success'])
        self.assertEqual(resp_data['sold_qty'], 10)
        self.assertEqual(resp_data['amount'], 5000)

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 130)

        sheet = SalesSheet.objects.get(item=product, branch=self.branch)
        self.assertEqual(sheet.sold_stock, 10)
        self.assertEqual(float(sheet.amount), 5000)

    def test_wine_remaining_exceeds_total_returns_error(self):
        product = self._create_product(
            name='Test Wine 2',
            unit_type='wine_glass',
            bottle_quantity=140,
            liters_per_unit=5,
            glasses_per_liter=28,
        )
        url = reverse('sales:create_sale')
        data = {
            'product_id': product.id,
            'remaining_glasses': 200,
            'payment_method': 'cash',
            'amount_paid': '0',
        }
        response = self.client.post(
            url, data=json.dumps(data), content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot exceed', response.json()['error'])

    def test_wine_negative_returns_error(self):
        product = self._create_product(
            name='Test Wine 3',
            unit_type='wine_glass',
            bottle_quantity=140,
            liters_per_unit=5,
            glasses_per_liter=28,
        )
        url = reverse('sales:create_sale')
        data = {
            'product_id': product.id,
            'remaining_glasses': -5,
            'payment_method': 'cash',
            'amount_paid': '0',
        }
        response = self.client.post(
            url, data=json.dumps(data), content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Negative', response.json()['error'])

    def test_wine_remaining_equals_total_returns_error(self):
        product = self._create_product(
            name='Test Wine 4',
            unit_type='wine_glass',
            bottle_quantity=140,
            liters_per_unit=5,
            glasses_per_liter=28,
        )
        url = reverse('sales:create_sale')
        data = {
            'product_id': product.id,
            'remaining_glasses': 140,
            'payment_method': 'cash',
            'amount_paid': '0',
        }
        response = self.client.post(
            url, data=json.dumps(data), content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('No stock sold', response.json()['error'])

    def test_wine_display_stock_and_properties(self):
        product = self._create_product(
            name='Test Wine Display',
            unit_type='wine_glass',
            bottle_quantity=45360,
            liters_per_unit=5,
            glasses_per_liter=28,
        )
        self.assertEqual(product.total_glasses, 45360)
        self.assertEqual(product.total_liters, 8100)
        self.assertIn('Glasses', product.display_stock)
        self.assertIn('8100L', product.display_stock)

    def test_wine_refund_restores_glasses(self):
        product = self._create_product(
            name='Test Wine Refund',
            unit_type='wine_glass',
            bottle_quantity=140,
            liters_per_unit=5,
            glasses_per_liter=28,
            selling_price=500,
        )
        url = reverse('sales:create_sale')
        data = {
            'product_id': product.id,
            'remaining_glasses': 120,
            'payment_method': 'cash',
            'amount_paid': '10000',
        }
        response = self.client.post(
            url, data=json.dumps(data), content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        sale_id = response.json()['sale_id']

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 120)

        self.client.post(reverse('sales:refund_sale', args=[sale_id]))

        product.refresh_from_db()
        self.assertEqual(product.bottle_quantity, 140)
