import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create or update a user to be superuser with role Super Admin."

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--email', default='')
        parser.add_argument('--password', default='')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        email = options['email'] or f'{username}@localhost'
        password = options['password']

        user = User.objects.filter(username=username).first()
        if user:
            user.is_superuser = True
            user.is_staff = True
            user.role = User.Role.SUPER_ADMIN
            if password:
                user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Updated existing user '{username}' to Super Admin.")
            )
        else:
            # Generate a unique referral code
            referral_code = uuid.uuid4().hex[:8].upper()
            while User.objects.filter(referral_code=referral_code).exists():
                referral_code = uuid.uuid4().hex[:8].upper()

            # Build user object with referral_code before saving
            user = User(
                username=username,
                email=email,
                is_superuser=True,
                is_staff=True,
                role=User.Role.SUPER_ADMIN,
                referral_code=referral_code,
            )
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Created Super Admin user '{username}'.")
            )
