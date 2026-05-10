import random
from django.core.management.base import BaseCommand
from inventory.models import Category, Product
from django.utils import timezone


CATEGORIES = {
    'Beers & Softs': 'Beers, soft drinks, and non-alcoholic beverages',
    'Ciders & Wines': 'Ciders, wines, and premium bottled drinks',
    'Spirits & Others': 'Spirits, liquors, mixers, and miscellaneous items',
    'Seed Products': 'Agricultural seed products',
}

BEERS_SOFTS = [
    ('Chill', 5000), ('Green', 4000), ('Special', 4000),
    ('KucheKuche', 4000), ('Pomme Breeze', 5000), ('Castel', 3500),
    ('Sapitwa', 3500), ('Dopel', 3500), ('CocaCola', 2000),
    ('Fanta', 2000), ('CherryPlum', 2000), ('Cocopina', 2000),
    ('Sobo Ginger', 2000), ('CocaCola Pet', 2000), ('Fanta Pet', 2000),
    ('Sprite', 2000), ('Sprite Pet', 2000), ('Malawi Gin 750ML', 30000),
    ('Premier Brandy 750ML', 40000), ('Malawi Vodka 750ML', 23000),
    ('Baby Gin', 15000), ('Baby Brandy', 20000), ('Baby Vodka', 10000),
]

SPIRITS_OTHERS = [
    ('Premier Brandy', 2500), ('Malawi Gin', 2500), ('Malawi Vodka', 2500),
    ('Capestars Vodka', 2500), ('Harrier', 2500), ('TimeOut', 2500),
    ('Ngwazi', 2500), ('Kho Brandy', 2500), ('KWV Brandy', 2500),
    ('Ancient Gin', 2500), ('Rassan', 2500), ('Konyage', 3000),
    ('Best Cream', 4000), ('Captain Morgan', 5000), ('Imperial Blue', 5000),
    ('Best Whiskey', 5000), ('Strawberry Lips', 5000), ('Smirnoff Vodka', 5000),
    ('Vat 69', 5000), ('Grants Whisky', 5000), ('Glenbrynth Scotch', 5000),
    ('Malibu', 5000), ('Libido', 6000), ('Amarula', 6000),
    ('Zappa', 6000), ('Red Lebel', 6000), ('Jagemeister', 8000),
    ('Black Lebel', 8000), ('Jameson', 8000), ('Chivas Regal', 8000),
    ('Tequila Silver', 8000), ('Tequila Gold', 8000), ('Tequila Black', 8000),
    ('Cactus Jack', 8000), ('Absolute Vanilla', 10000), ('Absolute Vodka', 10000),
    ('Jack Daniel Whiskey', 10000), ('Jack Daniel Honey', 10000),
    ('Gentleman Jack', 10000), ('Brains', 10000), ('Ponchos', 10000),
    ('Hennessy Gognac', 12000), ('Jameson Select', 12000), ('Double Black', 12000),
    ('Glenfiddich 12yrs', 12000), ('Monkey Shoulder', 12000), ('Wild Cat', 3000),
    ('Azam', 3000), ('Embe Small', 2500), ('Embe Big', 3000),
    ('Ukwaju Small', 2500), ('Ukwaju Big', 3000), ('Kombucha', 3000),
    ('Maheu', 3000), ('Fruitcana', 3000), ('Devine Power', 3000),
    ('Revin', 7000), ('Bottled Water', 1000), ('Straw', 1000),
    ('Disposable', 500), ('Gondolosi', 1500),
]

CIDERS_WINES = [
    ('Hunters Dry', 10000), ('Hunters Gold', 10000), ('Savanna', 10000),
    ('Savanna Big', 12000), ('Breezer', 10000), ('Brutal Fruit', 10000),
    ('Brutal Fruit Cane', 12000), ('Castle Light', 10000),
    ('Castle Light Cane', 10000), ('Heineken', 10000), ('Bernin', 12000),
    ('Amstel', 10000), ('Corona', 12000), ('Miller', 10000),
    ('Budwiser', 12000), ('Flying Fish', 10000), ('Flying Fish Cane', 12000),
    ('Drought', 12000), ('Fruit Tree', 10000), ('Dragon', 5000),
    ('RedBull', 8000), ('Soda Water', 5000), ('Tonic Water', 5000),
    ('Licufit', 8000), ('Grappetizer', 8000), ('Roses', 1500),
    ('Overmeer White', 5000), ('Overmeer Red', 5000), ('Overmeer Harvest', 5000),
    ('4th Street', 5000), ('Namaqua', 5000), ('Cellar Cask', 5000),
    ('Drostody Hof', 5000),
]

PRODUCTS_BY_CATEGORY = [
    ('Beers & Softs', BEERS_SOFTS),
    ('Ciders & Wines', CIDERS_WINES),
    ('Spirits & Others', SPIRITS_OTHERS),
    ('Seed Products', []),
]


CRATE_PRODUCTS = [
    'Chill', 'Green', 'Special', 'KucheKuche', 'Pomme Breeze',
    'Castel', 'Sapitwa', 'Dopel', 'CocaCola', 'Fanta',
    'CherryPlum', 'Cocopina', 'Sobo Ginger', 'Sprite',
    'Baby Gin', 'Baby Brandy', 'Baby Vodka',
    'CocaCola Pet', 'Fanta Pet', 'Sprite Pet',
    'Malawi Gin 750ML', 'Premier Brandy 750ML', 'Malawi Vodka 750ML',
]


def random_stock(selling_price):
    if selling_price >= 20000:
        return random.randint(5, 30)
    elif selling_price >= 10000:
        return random.randint(10, 50)
    elif selling_price >= 5000:
        return random.randint(20, 80)
    elif selling_price >= 2000:
        return random.randint(50, 200)
    else:
        return random.randint(100, 500)


def estimate_buying_price(selling_price):
    ratio = random.uniform(0.55, 0.70)
    return round(selling_price * ratio, -2)


def reorder_level(selling_price):
    if selling_price >= 20000:
        return 5
    elif selling_price >= 10000:
        return 10
    elif selling_price >= 5000:
        return 15
    elif selling_price >= 2000:
        return 30
    else:
        return 50


PACK_PRODUCTS = [
    'Hunters Dry', 'Hunters Gold', 'Savanna', 'Savanna Big', 'Breezer',
    'Brutal Fruit', 'Brutal Fruit Cane', 'Castle Light', 'Castle Light Cane',
    'Heineken', 'Bernin', 'Amstel', 'Corona', 'Miller', 'Budwiser',
    'Flying Fish', 'Flying Fish Cane', 'Drought', 'Fruit Tree', 'Dragon',
    'RedBull', 'Soda Water', 'Tonic Water', 'Licufit', 'Grappetizer',
]

SHOT_PRODUCTS = [
    'Premier Brandy', 'Malawi Gin', 'Malawi Vodka', 'Capestars Vodka',
    'Harrier', 'TimeOut', 'Ngwazi', 'Kho Brandy', 'KWV Brandy',
    'Ancient Gin', 'Rassan', 'Konyage', 'Best Cream', 'Captain Morgan',
    'Imperial Blue', 'Best Whiskey', 'Strawberry Lips', 'Smirnoff Vodka',
    'Vat 69', 'Grants Whisky', 'Glenbrynth Scotch', 'Malibu', 'Libido',
    'Amarula', 'Zappa', 'Red Lebel', 'Jagemeister', 'Black Lebel',
    'Jameson', 'Chivas Regal', 'Tequila Silver', 'Tequila Gold',
    'Tequila Black', 'Cactus Jack', 'Absolute Vanilla', 'Absolute Vodka',
    'Jack Daniel Whiskey', 'Jack Daniel Honey', 'Gentleman Jack',
    'Brains', 'Ponchos', 'Hennessy Gognac', 'Jameson Select',
    'Double Black', 'Glenfiddich 12yrs', 'Monkey Shoulder',
]


def random_pack_stock(selling_price):
    if selling_price >= 10000:
        return random.randint(2, 10)
    elif selling_price >= 5000:
        return random.randint(5, 20)
    else:
        return random.randint(10, 30)


def random_bottle_stock(selling_price):
    if selling_price >= 10000:
        return random.randint(2, 8)
    elif selling_price >= 5000:
        return random.randint(3, 12)
    else:
        return random.randint(5, 20)


def random_crate_stock(selling_price):
    if selling_price >= 20000:
        return random.randint(1, 5)
    elif selling_price >= 10000:
        return random.randint(2, 8)
    elif selling_price >= 5000:
        return random.randint(3, 12)
    elif selling_price >= 2000:
        return random.randint(5, 20)
    else:
        return random.randint(10, 30)


class Command(BaseCommand):
    help = 'Seed the database with categories and products'

    def handle(self, *args, **options):
        self.stdout.write('Clearing existing products and categories...')
        Product.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write('Creating categories...')
        created_categories = {}
        for name, description in CATEGORIES.items():
            cat, _ = Category.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            created_categories[name] = cat
            self.stdout.write(f'  + Category: {name}')

        total_products = 0
        for cat_name, products in PRODUCTS_BY_CATEGORY:
            category = created_categories[cat_name]
            cat_order = 0
            for name, price in products:
                cat_order += 1
                buying = estimate_buying_price(price)
                reorder = reorder_level(price)
                is_crate = name in CRATE_PRODUCTS
                is_pack = name in PACK_PRODUCTS
                is_shot = name in SHOT_PRODUCTS
                if is_crate:
                    crates = random_crate_stock(price)
                    bottles = random.randint(0, 19)
                    Product.objects.create(
                        category=category,
                        name=name,
                        selling_price=price,
                        buying_price=buying,
                        reorder_level=reorder,
                        is_active=True,
                        unit_type='Crate',
                        units_per_crate=20,
                        selling_unit='Bottle',
                        crate_quantity=crates,
                        bottle_quantity=bottles,
                        display_order=cat_order,
                    )
                elif is_shot:
                    bottles = random_bottle_stock(price)
                    loose_shots = random.randint(0, 20)
                    Product.objects.create(
                        category=category,
                        name=name,
                        selling_price=price,
                        buying_price=buying,
                        reorder_level=reorder,
                        is_active=True,
                        unit_type='Bottle',
                        shots_per_bottle=21,
                        bottle_quantity=bottles,
                        shot_quantity=loose_shots,
                        selling_unit='Shot',
                        display_order=cat_order,
                    )
                elif is_pack:
                    packs = random_pack_stock(price)
                    loose = random.randint(0, 5)
                    Product.objects.create(
                        category=category,
                        name=name,
                        selling_price=price,
                        buying_price=buying,
                        reorder_level=reorder,
                        is_active=True,
                        unit_type='Pack',
                        units_per_pack=6,
                        pack_quantity=packs,
                        bottle_quantity=loose,
                        selling_unit='Bottle/Can',
                        display_order=cat_order,
                    )
                else:
                    stock = random_stock(price)
                    Product.objects.create(
                        category=category,
                        name=name,
                        selling_price=price,
                        buying_price=buying,
                        reorder_level=reorder,
                        is_active=True,
                        unit_type='Piece',
                        units_per_crate=1,
                        selling_unit='Piece',
                        crate_quantity=0,
                        bottle_quantity=stock,
                        display_order=cat_order,
                    )
                total_products += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {len(CATEGORIES)} categories and {total_products} products.'
        ))
