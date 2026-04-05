"""
Management command: create_superuser_if_missing

Creates a Django superuser from environment variables — idempotent and safe
to run on every Render deployment via build.sh.

Required env vars (only needed once; skipped if already set):
  DJANGO_SUPERUSER_USERNAME
  DJANGO_SUPERUSER_EMAIL
  DJANGO_SUPERUSER_PASSWORD

Example build.sh usage:
  python manage.py create_superuser_if_missing
"""

import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a superuser from env vars if one does not already exist.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        email    = os.environ.get('DJANGO_SUPERUSER_EMAIL',    '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '').strip()

        if not all([username, email, password]):
            self.stdout.write(
                self.style.WARNING(
                    'Skipping superuser creation: '
                    'DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and '
                    'DJANGO_SUPERUSER_PASSWORD env vars must all be set.'
                )
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" already exists — skipping.')
            )
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(
            self.style.SUCCESS(f'Superuser "{username}" created successfully.')
        )
