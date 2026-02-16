"""Seed SuperSetting with game API credentials (secret, token, callback URL) from api-doc."""
from django.core.management.base import BaseCommand

from core.models import SuperSetting


# Credentials from api-doc (Secret Key, Token, Callback URL)
GAME_API_SECRET = "4d45bba519ac2d39d1618f57120b84b7"
GAME_API_TOKEN = "184de030-912d-4c26-81fc-6c5cd3c05add"
GAME_API_CALLBACK_URL = "https://kingxclub.com/api/callback"


class Command(BaseCommand):
    help = (
        "Seed or update SuperSetting with game API secret, token, and callback URL. "
        "Optionally set game_api_url with --base-url."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            type=str,
            default=None,
            help="If provided, set game_api_url (e.g. https://YOUR_GAME_API_SERVER).",
        )

    def handle(self, *args, **options):
        obj = SuperSetting.objects.first()
        if obj is None:
            obj = SuperSetting()
        obj.game_api_secret = GAME_API_SECRET
        obj.game_api_token = GAME_API_TOKEN
        obj.game_api_callback_url = GAME_API_CALLBACK_URL
        base_url = options.get("base_url")
        if base_url:
            obj.game_api_url = base_url.strip()
        obj.save()
        self.stdout.write(
            self.style.SUCCESS(
                "SuperSetting seeded with game API secret, token, and callback URL."
            )
        )
        if base_url:
            self.stdout.write(self.style.SUCCESS(f"game_api_url set to: {base_url}"))
