"""Build encrypted payload and call launch_game API; print redirect URL."""
from django.core.management.base import BaseCommand

from core.game_api_client import launch_game
from core.models import SuperSetting


class Command(BaseCommand):
    help = "Launch a game via external API (encrypted payload). Requires --user-id, --wallet-amount, --game-uid, --token (or game_api_token in SuperSetting)."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", type=str, default=None, help="Base URL of game API.")
        parser.add_argument("--secret", type=str, default=None, help="API secret key (32 chars) for AES payload.")
        parser.add_argument("--token", type=str, default=None, help="API token for launch.")
        parser.add_argument("--user-id", type=str, required=True, help="User identifier.")
        parser.add_argument("--wallet-amount", type=float, required=True, help="User wallet balance (number).")
        parser.add_argument("--game-uid", type=str, required=True, help="Game/provider unique identifier.")

    def handle(self, *args, **options):
        base_url = options.get("base_url")
        secret = options.get("secret")
        token = options.get("token")
        settings = SuperSetting.get_settings()
        if not base_url and settings and settings.game_api_url:
            base_url = settings.game_api_url.strip()
        if not secret and settings and settings.game_api_secret:
            secret = settings.game_api_secret
        if not token and settings and getattr(settings, "game_api_token", None):
            token = settings.game_api_token
        if not base_url:
            self.stderr.write(self.style.ERROR("Missing base URL. Set --base-url or game_api_url in SuperSetting."))
            return
        if not secret:
            self.stderr.write(self.style.ERROR("Missing secret. Set --secret or game_api_secret in SuperSetting."))
            return
        if not token:
            self.stderr.write(self.style.ERROR("Missing token. Set --token or game_api_token in SuperSetting."))
            return
        try:
            r = launch_game(
                base_url=base_url,
                secret_key=secret,
                token=token,
                user_id=options["user_id"],
                wallet_amount=options["wallet_amount"],
                game_uid=options["game_uid"],
                allow_redirects=False,
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Launch error: {e}"))
            return
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            self.stdout.write(self.style.SUCCESS(f"Open: {r.headers['Location']}"))
        elif r.status_code == 200:
            try:
                self.stdout.write(r.text[:500])
            except Exception:
                self.stdout.write(f"Status {r.status_code}, no redirect.")
        else:
            self.stdout.write(self.style.WARNING(f"Status {r.status_code}: {r.text[:300]}"))
