from django.core.management.base import BaseCommand
from branches.models import Branch


BRAND_COLORS = {
    'Azibambo Stop Over': {
        'theme_color': '#6B3E2E',
        'secondary_color': '#8B5E3C',
        'logo_background_color': '#4A2A1E',
        'theme_mode': 'dark',
        'sidebar_bg': '#3A1F12',
        'sidebar_text': '#e8d5c4',
        'header_bg': '#6B3E2E',
        'header_text': '#ffffff',
        'selection_bg': '#8B5E3C',
        'selection_text': '#ffffff',
        'button_color': '#6B3E2E',
        'card_accent': '#8B5E3C',
        'widget_bg': '#2D180E',
    },
    'CV Lounge': {
        'theme_color': '#6A0DAD',
        'secondary_color': '#9B30FF',
        'logo_background_color': '#3B0764',
        'theme_mode': 'dark',
        'sidebar_bg': '#2D054A',
        'sidebar_text': '#e0c8f0',
        'header_bg': '#6A0DAD',
        'header_text': '#ffffff',
        'selection_bg': '#9B30FF',
        'selection_text': '#ffffff',
        'button_color': '#6A0DAD',
        'card_accent': '#9B30FF',
        'widget_bg': '#1E0336',
    },
    'Main Warehouse': {
        'theme_color': '#374151',
        'secondary_color': '#4B5563',
        'logo_background_color': '#111827',
        'theme_mode': 'dark',
        'sidebar_bg': '#1f2937',
        'sidebar_text': '#d1d5db',
        'header_bg': '#374151',
        'header_text': '#ffffff',
        'selection_bg': '#4B5563',
        'selection_text': '#ffffff',
        'button_color': '#374151',
        'card_accent': '#4B5563',
        'widget_bg': '#111827',
    },
}


class Command(BaseCommand):
    help = 'Seed demo branches'

    def handle(self, *args, **options):
        branches_data = [
            {
                'branch_code': 'AZB-001',
                'branch_name': 'Azibambo Stop Over',
                'branch_type': 'Bar',
                'phone': '+265 999 000 001',
                'email': 'azibambo@azibambo.com',
                'address': 'Area 47, Lilongwe',
            },
            {
                'branch_code': 'CVL-001',
                'branch_name': 'CV Lounge',
                'branch_type': 'Club',
                'phone': '+265 999 000 002',
                'email': 'cvlounge@azibambo.com',
                'address': 'Area 25, Lilongwe',
            },
            {
                'branch_code': 'WH-001',
                'branch_name': 'Main Warehouse',
                'branch_type': 'Warehouse',
                'phone': '+265 999 000 003',
                'email': 'warehouse@azibambo.com',
                'address': 'Industrial Area, Lilongwe',
            },
        ]

        for data in branches_data:
            colors = BRAND_COLORS.get(data['branch_name'], {})
            defaults = {**data, **colors}
            branch, created = Branch.objects.update_or_create(
                branch_code=data['branch_code'],
                defaults=defaults
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created branch: {branch.branch_name} [{branch.theme_color}]'))
            else:
                self.stdout.write(f'Updated branch: {branch.branch_name} [{branch.theme_color}]')

        self.stdout.write(self.style.SUCCESS('Demo branches seeded successfully!'))
