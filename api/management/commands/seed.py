import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from api.models import Category

CATEGORIES = [
    'Uncategorized', 'Food', 'Transport', 'Airtime & Data', 'Rent',
    'School Fees', 'Books & Stationery', 'Entertainment', 'Health',
]


class Command(BaseCommand):
    help = 'Adds the starter categories and one admin account (safe to run twice)'

    def handle(self, *args, **options):
        for name in CATEGORIES:
            Category.objects.get_or_create(name=name)

        password = os.environ.get('ADMIN_PASSWORD', 'Admin#12345')
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@pesasave.com', password)
            self.stdout.write(self.style.SUCCESS('Admin user created.'))
        self.stdout.write(self.style.SUCCESS(f'{len(CATEGORIES)} categories ready.'))