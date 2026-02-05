from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates test users with the hierarchy: powerhouse -> super -> master'

    def handle(self, *args, **options):
        self.stdout.write('Creating test users...\n')

        # Create Powerhouse user
        powerhouse, created = User.objects.get_or_create(
            username='powerhouse',
            defaults={
                'email': 'powerhouse@karnalix.com',
                'role': 'POWERHOUSE',
                'status': 'ACTIVE',
                'is_staff': True,
            }
        )
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
            }
        )
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

        self.stdout.write('\n' + self.style.SUCCESS('Test users creation completed!'))
        self.stdout.write('\nUser hierarchy:')
        self.stdout.write('  powerhouse (POWERHOUSE) - no parent')
        self.stdout.write('  └── super (SUPER) - parent: powerhouse')
        self.stdout.write('      └── master (MASTER) - parent: super')
        self.stdout.write('\nAll passwords: 12345678')
