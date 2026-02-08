from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from core.models import PaymentMode

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates test users with the hierarchy: powerhouse -> super -> master. Use --fresh to delete all users first.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fresh',
            action='store_true',
            help='Delete all users first, then create test users.',
        )

    def handle(self, *args, **options):
        if options['fresh']:
            count, _ = User.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} user(s).'))
            self.stdout.write('Creating test users...\n')
        else:
            self.stdout.write('Creating test users...\n')

        # Create Powerhouse user
        powerhouse, created = User.objects.get_or_create(
            username='powerhouse',
            defaults={
                'email': 'powerhouse@karnalix.com',
                'role': 'POWERHOUSE',
                'status': 'ACTIVE',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if not created:
            powerhouse.is_superuser = True
            powerhouse.save(update_fields=['is_superuser'])
        if created:
            powerhouse.set_password('12345678')
            powerhouse.save()
            self.stdout.write(self.style.SUCCESS(f'Created POWERHOUSE user: powerhouse (password: 12345678)'))
        else:
            self.stdout.write(self.style.WARNING(f'POWERHOUSE user already exists: powerhouse'))

        # Create Super user with parent -> powerhouse
        super_user, created = User.objects.get_or_create(
            username='super',
            defaults={
                'email': 'super@karnalix.com',
                'role': 'SUPER',
                'status': 'ACTIVE',
                'parent': powerhouse,
                'is_superuser': True,
            }
        )
        if not created:
            super_user.is_superuser = True
            super_user.save(update_fields=['is_superuser'])
        if created:
            super_user.set_password('12345678')
            super_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created SUPER user: super (password: 12345678, parent: powerhouse)'))
        else:
            self.stdout.write(self.style.WARNING(f'SUPER user already exists: super'))

        # Create Master user with parent -> super
        master, created = User.objects.get_or_create(
            username='master',
            defaults={
                'email': 'master@karnalix.com',
                'role': 'MASTER',
                'status': 'ACTIVE',
                'parent': super_user,
            }
        )
        if created:
            master.set_password('12345678')
            master.save()
            self.stdout.write(self.style.SUCCESS(f'Created MASTER user: master (password: 12345678, parent: super)'))
        else:
            self.stdout.write(self.style.WARNING(f'MASTER user already exists: master'))

        # Create a USER under master (so they see parent payment methods on deposit)
        user1, created = User.objects.get_or_create(
            username='user1',
            defaults={
                'email': 'user1@test.com',
                'role': 'USER',
                'status': 'ACTIVE',
                'parent': master,
                'referred_by': master,
            }
        )
        if created:
            user1.set_password('12345678')
            user1.save()
            self.stdout.write(self.style.SUCCESS(f'Created USER: user1 (password: 12345678, parent: master)'))
        else:
            if user1.parent_id != master.id:
                user1.parent = master
                user1.referred_by = master
                user1.save(update_fields=['parent', 'referred_by'])
                self.stdout.write(self.style.WARNING(f'Updated user1 parent to master'))

        # Ensure master has at least one payment mode (for user deposit flow)
        pm, created = PaymentMode.objects.get_or_create(
            user=master,
            wallet_holder_name='Master Khalti',
            defaults={
                'type': PaymentMode.PaymentType.EWALLET,
                'wallet_phone': '',
                'status': PaymentMode.Status.ACTIVE,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created payment mode for master: {pm.wallet_holder_name}'))
        if not pm.status == PaymentMode.Status.ACTIVE:
            pm.status = PaymentMode.Status.ACTIVE
            pm.save(update_fields=['status'])

        self.stdout.write('\n' + self.style.SUCCESS('Test users creation completed!'))
        self.stdout.write('\nUser hierarchy:')
        self.stdout.write('  powerhouse (POWERHOUSE) - no parent, is_superuser=True')
        self.stdout.write('  -> super (SUPER) - parent: powerhouse, is_superuser=True')
        self.stdout.write('      -> master (MASTER) - parent: super')
        self.stdout.write('          -> user1 (USER) - parent: master')
        self.stdout.write('\nAll passwords: 12345678')
        self.stdout.write('Log in as user1 to test deposit with parent (master) payment methods.')
