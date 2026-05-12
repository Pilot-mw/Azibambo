from django.test import TestCase
from inventory.services.conversion_engine import (
    get_conversion_rate, get_purchase_unit, get_selling_unit,
    get_purchase_unit_label, get_selling_unit_label,
    convert_purchase_to_base, convert_base_to_warehouse,
    calculate_sold, calculate_amount, validate_stock_input,
    convert_for_display, get_pos_input_fields,
)
from inventory.models import Product, Category


class ConversionEngineTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name='Test')
        cls.crate = Product.objects.create(
            name='Test Crate', category=cls.cat, unit_type='Crate',
            crate_size=20, conversion_rate=20, purchase_unit='Crate',
            selling_price=1000, bottle_quantity=100,
        )
        cls.pack = Product.objects.create(
            name='Test Pack', category=cls.cat, unit_type='Pack',
            pack_size=6, conversion_rate=6, purchase_unit='Pack',
            selling_price=500, bottle_quantity=60,
        )
        cls.bottle = Product.objects.create(
            name='Test Bottle', category=cls.cat, unit_type='Bottle',
            conversion_rate=1, purchase_unit='Bottle',
            selling_price=2000, bottle_quantity=10,
        )
        cls.shot = Product.objects.create(
            name='Test Shot', category=cls.cat, unit_type='Bottle',
            shots_per_bottle=21, conversion_rate=21, purchase_unit='Bottle',
            bottle_quantity=5, shot_quantity=10, selling_price=21000,
        )
        cls.wine = Product.objects.create(
            name='Test Wine', category=cls.cat, unit_type='wine_glass',
            glasses_per_liter=28, liters_per_unit=5,
            conversion_rate=28, purchase_unit='Container',
            bottle_quantity=1232, selling_price=500,
        )

    def test_get_conversion_rate(self):
        self.assertEqual(get_conversion_rate(self.crate), 20)
        self.assertEqual(get_conversion_rate(self.pack), 6)
        self.assertEqual(get_conversion_rate(self.bottle), 1)
        self.assertEqual(get_conversion_rate(self.shot), 21)
        self.assertEqual(get_conversion_rate(self.wine), 28)

    def test_get_purchase_unit(self):
        self.assertEqual(get_purchase_unit(self.crate), 'Crate')
        self.assertEqual(get_purchase_unit(self.pack), 'Pack')
        self.assertEqual(get_purchase_unit(self.bottle), 'Bottle')
        self.assertEqual(get_purchase_unit(self.shot), 'Bottle')
        self.assertEqual(get_purchase_unit(self.wine), 'Container')

    def test_get_selling_unit(self):
        self.assertEqual(get_selling_unit(self.crate), 'Bottle')
        self.assertEqual(get_selling_unit(self.pack), 'Bottle')
        self.assertEqual(get_selling_unit(self.bottle), 'Bottle')
        self.assertEqual(get_selling_unit(self.shot), 'Shot')
        self.assertEqual(get_selling_unit(self.wine), 'Glass')

    def test_get_purchase_unit_label(self):
        self.assertEqual(get_purchase_unit_label(self.wine), 'Containers')
        self.assertEqual(get_purchase_unit_label(self.crate), 'Crates')
        self.assertEqual(get_purchase_unit_label(self.pack), 'Packs')
        self.assertEqual(get_purchase_unit_label(self.bottle), 'Bottles')

    def test_get_selling_unit_label(self):
        self.assertEqual(get_selling_unit_label(self.crate), 'Bottles')
        self.assertEqual(get_selling_unit_label(self.wine), 'Glasses')
        self.assertEqual(get_selling_unit_label(self.shot), 'Shots')

    def test_convert_purchase_to_base(self):
        self.assertEqual(convert_purchase_to_base(5, self.crate), 100)  # 5*20
        self.assertEqual(convert_purchase_to_base(4, self.pack), 24)    # 4*6
        self.assertEqual(convert_purchase_to_base(3, self.bottle), 3)   # 3*1
        self.assertEqual(convert_purchase_to_base(2, self.shot), 42)    # 2*21
        self.assertEqual(convert_purchase_to_base(10, self.wine), 280)  # 10*28

    def test_convert_base_to_warehouse(self):
        self.assertEqual(convert_base_to_warehouse(100, self.crate), (5, 0))
        self.assertEqual(convert_base_to_warehouse(25, self.pack), (4, 1))
        self.assertEqual(convert_base_to_warehouse(3, self.bottle), (3, 0))
        self.assertEqual(convert_base_to_warehouse(50, self.shot), (2, 8))
        self.assertEqual(convert_base_to_warehouse(300, self.wine), (10, 20))

    def test_calculate_sold(self):
        self.assertEqual(calculate_sold(100, 60), 40)
        with self.assertRaises(ValueError):
            calculate_sold(100, -1)
        with self.assertRaises(ValueError):
            calculate_sold(100, 120)

    def test_calculate_amount(self):
        self.assertEqual(calculate_amount(10, 500), 5000)

    def test_validate_stock_input_valid(self):
        valid, result = validate_stock_input(60, 100)
        self.assertTrue(valid)
        self.assertEqual(result, 40)

    def test_validate_stock_input_negative(self):
        valid, result = validate_stock_input(-1, 100)
        self.assertFalse(valid)
        self.assertIn('Negative', result)

    def test_validate_stock_input_exceeds(self):
        valid, result = validate_stock_input(120, 100)
        self.assertFalse(valid)
        self.assertIn('exceed', result)

    def test_validate_stock_input_zero_sold(self):
        valid, result = validate_stock_input(100, 100)
        self.assertFalse(valid)
        self.assertIn('No stock sold', result)

    def test_convert_for_display_sales(self):
        result = convert_for_display(100, self.crate, 'sales')
        self.assertIn('100', result)
        self.assertIn('Bottles', result)

    def test_convert_for_display_warehouse(self):
        result = convert_for_display(100, self.crate, 'warehouse')
        self.assertIn('5', result)
        self.assertIn('Crates', result)

    def test_get_pos_input_fields(self):
        self.assertEqual(get_pos_input_fields(self.wine)['input_label'], 'Remaining Glasses')
        self.assertEqual(get_pos_input_fields(self.shot)['input_label'], 'Remaining Shots')
        self.assertEqual(get_pos_input_fields(self.crate)['input_label'], 'Remaining Bottles')

    def test_conversion_rate_field_backfilled(self):
        """Verify backfill migration set correct values"""
        self.assertEqual(self.crate.conversion_rate, 20)
        self.assertEqual(self.pack.conversion_rate, 6)
        self.assertEqual(self.bottle.conversion_rate, 1)
        self.assertEqual(self.wine.conversion_rate, 28)

    def test_purchase_unit_field_backfilled(self):
        self.assertEqual(self.crate.purchase_unit, 'Crate')
        self.assertEqual(self.pack.purchase_unit, 'Pack')
        self.assertEqual(self.bottle.purchase_unit, 'Bottle')
        self.assertEqual(self.wine.purchase_unit, 'Container')


class ConversionEngineFallbackTest(TestCase):
    """Tests that engine falls back to legacy fields when conversion_rate/purchase_unit are not set"""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name='Test')
        cls.crate = Product.objects.create(
            name='Crate Fallback', category=cls.cat, unit_type='Crate',
            crate_size=24, conversion_rate=None, purchase_unit='',
            bottle_quantity=100,
        )
        cls.pack = Product.objects.create(
            name='Pack Fallback', category=cls.cat, unit_type='Pack',
            pack_size=8, conversion_rate=None, purchase_unit='',
            bottle_quantity=100,
        )
        cls.bottle = Product.objects.create(
            name='Bottle Fallback', category=cls.cat, unit_type='Bottle',
            conversion_rate=None, purchase_unit='',
            bottle_quantity=100,
        )
        cls.wine = Product.objects.create(
            name='Wine Fallback', category=cls.cat, unit_type='wine_glass',
            glasses_per_liter=28, liters_per_unit=5,
            conversion_rate=None, purchase_unit='',
            bottle_quantity=1232,
        )

    def test_fallback_conversion_rate(self):
        self.assertEqual(get_conversion_rate(self.crate), 24)
        self.assertEqual(get_conversion_rate(self.pack), 8)
        self.assertEqual(get_conversion_rate(self.bottle), 1)
        self.assertEqual(get_conversion_rate(self.wine), 28)

    def test_fallback_purchase_unit(self):
        self.assertEqual(get_purchase_unit(self.crate), 'Crate')
        self.assertEqual(get_purchase_unit(self.pack), 'Pack')
        self.assertEqual(get_purchase_unit(self.bottle), 'Bottle')
        self.assertEqual(get_purchase_unit(self.wine), 'Container')

    def test_fallback_convert_purchase_to_base(self):
        self.assertEqual(convert_purchase_to_base(5, self.crate), 120)
        self.assertEqual(convert_purchase_to_base(3, self.pack), 24)
        self.assertEqual(convert_purchase_to_base(10, self.wine), 280)
