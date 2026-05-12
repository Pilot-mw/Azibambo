PURCHASE_UNIT_CHOICES = [
    ('Crate', 'Crate'),
    ('Pack', 'Pack'),
    ('Bottle', 'Bottle'),
    ('Container', 'Container'),
]

SELLING_UNIT_CHOICES_ENGINE = [
    ('Bottle', 'Bottle'),
    ('Shot', 'Shot'),
    ('Glass', 'Glass'),
]

UNIT_FAMILIES = {
    'Crate': {
        'purchase_unit': 'Crate',
        'selling_unit': 'Bottle',
        'default_rate_field': 'crate_size',
        'default_rate': 20,
    },
    'Pack': {
        'purchase_unit': 'Pack',
        'selling_unit': 'Bottle',
        'default_rate_field': 'pack_size',
        'default_rate': 6,
    },
    'Bottle': {
        'purchase_unit': 'Bottle',
        'selling_unit': 'Bottle',
        'default_rate_field': None,
        'default_rate': 1,
    },
    'wine_glass': {
        'purchase_unit': 'Container',
        'selling_unit': 'Glass',
        'default_rate_field': 'glasses_per_liter',
        'default_rate': 28,
    },
}


def _get_rate(product):
    if product.conversion_rate:
        return product.conversion_rate
    family = UNIT_FAMILIES.get(product.unit_type, {})
    field_name = family.get('default_rate_field')
    if field_name and hasattr(product, field_name):
        return getattr(product, field_name) or family['default_rate']
    return family.get('default_rate', 1)


def _get_purchase_unit(product):
    if product.purchase_unit:
        return product.purchase_unit
    family = UNIT_FAMILIES.get(product.unit_type, {})
    return family.get('purchase_unit', 'Bottle')


def _get_selling_unit(product):
    if product.selling_unit and product.selling_unit != 'Bottle':
        return product.selling_unit
    if product.unit_type == 'wine_glass':
        return 'Glass'
    if product.unit_type == 'Bottle' and product.shots_per_bottle and product.shots_per_bottle > 1:
        return 'Shot'
    return 'Bottle'


def get_purchase_unit_label(product):
    unit = _get_purchase_unit(product)
    return unit + 's' if unit != 'Container' else 'Containers'


def get_selling_unit_label(product):
    unit = _get_selling_unit(product)
    if unit == 'Glass':
        return 'Glasses'
    return unit + 's'


def convert_purchase_to_base(warehouse_qty, product):
    rate = _get_rate(product)
    return warehouse_qty * rate


def convert_base_to_warehouse(base_qty, product):
    rate = _get_rate(product)
    if rate:
        return divmod(base_qty, rate)
    return (base_qty, 0)


def convert_for_display(qty, product, context='sales'):
    if context == 'warehouse':
        containers, remainder = convert_base_to_warehouse(qty, product)
        unit_label = get_purchase_unit_label(product)
        return f"{containers} {unit_label}"
    unit_label = get_selling_unit_label(product)
    return f"{qty} {unit_label}"


def get_selling_unit(product):
    return _get_selling_unit(product)


def get_purchase_unit(product):
    return _get_purchase_unit(product)


def get_conversion_rate(product):
    return _get_rate(product)


def calculate_sold(total_stock, remaining_stock):
    if total_stock < 0 or remaining_stock < 0:
        raise ValueError("Negative stock values not allowed")
    if remaining_stock > total_stock:
        raise ValueError("Remaining cannot exceed total")
    return total_stock - remaining_stock


def calculate_amount(sold_qty, selling_price):
    return sold_qty * float(selling_price)


def validate_stock_input(remaining, total):
    if remaining < 0:
        return False, "Negative values not allowed"
    if remaining > total:
        return False, "Remaining cannot exceed total stock"
    sold = total - remaining
    if sold == 0:
        return False, "No stock sold. Remaining equals total."
    return True, sold


def get_pos_input_fields(product):
    unit = _get_selling_unit(product)
    fields = {'input_label': f'Remaining {unit}s', 'input_id': 'remainingInput1'}
    if unit == 'Glass':
        fields = {'input_label': 'Remaining Glasses', 'input_id': 'wineRemainingGlasses'}
    elif unit == 'Shot':
        fields = {'input_label': 'Remaining Shots', 'input_id': 'remainingShots'}
    return fields
