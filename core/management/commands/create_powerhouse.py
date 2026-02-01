"""
Management command to create a PowerHouse (root) user.

Usage:
    python manage.py create_powerhouse --username admin --email admin@example.com --password admin123
"""

import uuid
from django.core.management.base import BaseCommand, CommandError
from core.models import User, Wallet, UserSettings


class Command(BaseCommand):
    help = 'Creates a PowerHouse (platform owner) user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='powerhouse',
            help='Username for the PowerHouse user'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='powerhouse@karnalix.com',
            help='Email for the PowerHouse user'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='powerhouse123',
            help='Password for the PowerHouse user'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        # Check if PowerHouse already exists
        if User.objects.filter(role=User.Role.POWERHOUSE).exists():
            existing = User.objects.filter(role=User.Role.POWERHOUSE).first()
            self.stdout.write(
                self.style.WARNING(
                    f'PowerHouse user already exists: {existing.username} ({existing.email})'
                )
            )
            return

        # Check for username/email conflicts
        if User.objects.filter(username__iexact=username).exists():
            raise CommandError(f'Username "{username}" already exists')
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f'Email "{email}" already exists')

        # Generate unique referral code
        referral_code = uuid.uuid4().hex[:8].upper()
        while User.objects.filter(referral_code=referral_code).exists():
            referral_code = uuid.uuid4().hex[:8].upper()

        # Create PowerHouse user
        user = User(
            username=username,
            email=email,
            name='PowerHouse Admin',
            role=User.Role.POWERHOUSE,
            referral_code=referral_code,
            is_staff=True,
            is_superuser=True,
        )
        user.set_password(password)
        user.save()

        # Create wallet and settings
        Wallet.objects.get_or_create(
            user=user,
            defaults={'balance': 0, 'currency': 'INR'}
        )
        UserSettings.objects.get_or_create(user=user)

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPowerHouse user created successfully!\n'
                f'  Username: {username}\n'
                f'  Email: {email}\n'
                f'  Password: {password}\n'
                f'  Role: PowerHouse\n'
                f'\nYou can now login at /login and access /powerhouse panel.'
            )
        )
