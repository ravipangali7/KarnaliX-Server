"""Seed or update JILI GameProvider with launch config (api_endpoint, api_secret, api_token). If provider exists and all fields already match, skip."""
from django.core.management.base import BaseCommand

from core.models import GameProvider


# JILI uses allapi launch; same defaults as SuperSetting for consistency
JILI_API_ENDPOINT = "https://allapi.online/launch_game1_js"
JILI_API_SECRET = "4d45bba519ac2d39d1618f57120b84b7"
JILI_API_TOKEN = "184de030-912d-4c26-81fc-6c5cd3c05add"


class Command(BaseCommand):
    help = (
        "Seed or update JILI GameProvider with api_endpoint, api_secret, api_token for game launch. "
        "If provider already exists and all required fields are set and match, skip."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--endpoint",
            type=str,
            default=None,
            help=f"Override api_endpoint (default: {JILI_API_ENDPOINT}).",
        )
        parser.add_argument(
            "--secret",
            type=str,
            default=None,
            help="Override api_secret.",
        )
        parser.add_argument(
            "--token",
            type=str,
            default=None,
            help="Override api_token.",
        )

    def handle(self, *args, **options):
        endpoint = (options.get("endpoint") or JILI_API_ENDPOINT).strip()
        secret = (options.get("secret") or JILI_API_SECRET).strip()
        token = (options.get("token") or JILI_API_TOKEN).strip()

        provider, created = GameProvider.objects.get_or_create(
            code="jili",
            defaults={
                "name": "JILI",
                "is_active": True,
                "api_endpoint": endpoint,
                "api_secret": secret,
                "api_token": token,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS("Created JILI provider with api_endpoint, api_secret, api_token.")
            )
            return

        # Already exists: update only if something is missing or different
        updated = False
        if (provider.api_endpoint or "").strip() != endpoint:
            provider.api_endpoint = endpoint
            updated = True
        if (provider.api_secret or "").strip() != secret:
            provider.api_secret = secret
            updated = True
        if (provider.api_token or "").strip() != token:
            provider.api_token = token
            updated = True

        if updated:
            provider.save()
            self.stdout.write(
                self.style.SUCCESS("Updated JILI provider: api_endpoint, api_secret, api_token.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("JILI provider already has required fields; skipped.")
            )
