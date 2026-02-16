"""Call external providerGame API and print game list."""
import json
from django.core.management.base import BaseCommand

from core.game_api_client import get_provider_games
from core.models import SuperSetting


class Command(BaseCommand):
    help = "Fetch games for a provider (providerGame). Requires --provider. Use --base-url or SuperSetting."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            type=str,
            default=None,
            help="Base URL of game API. Overrides SuperSetting.",
        )
        parser.add_argument(
            "--provider",
            type=str,
            required=True,
            help="Provider code (e.g. jili).",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Max number of games to fetch (default: 50).",
        )
        parser.add_argument(
            "--type",
            dest="game_type",
            type=str,
            default=None,
            help="Optional game type/category filter (e.g. slotgame).",
        )
        parser.add_argument(
            "--output",
            type=str,
            choices=["json", "table"],
            default="table",
            help="Output format (default: table).",
        )

    def handle(self, *args, **options):
        base_url = options.get("base_url")
        if not base_url:
            settings = SuperSetting.get_settings()
            if settings and settings.game_api_url:
                base_url = settings.game_api_url.strip()
        if not base_url:
            self.stderr.write(
                self.style.ERROR("Missing base URL. Set --base-url or game_api_url in SuperSetting.")
            )
            return
        provider = options["provider"]
        count = options["count"]
        game_type = options.get("game_type")
        try:
            games = get_provider_games(base_url, provider, count=count, game_type=game_type)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"API error: {e}"))
            return
        if options["output"] == "json":
            self.stdout.write(json.dumps(games, indent=2))
        else:
            if not games:
                self.stdout.write("No games returned.")
                return
            self.stdout.write(f"{'name':<40}  {'code':<30}  {'type':<20}  image")
            self.stdout.write("-" * 100)
            for g in games:
                name = (g.get("game_name") or "")[:38]
                code = (g.get("game_code") or "")[:28]
                typ = (g.get("game_type") or "")[:18]
                img = (g.get("game_image") or "")[:40]
                self.stdout.write(f"{name:<40}  {code:<30}  {typ:<20}  {img}")
        self.stdout.write(self.style.SUCCESS(f"Done. {len(games)} game(s)."))
