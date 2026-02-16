"""Call external getProvider API and print provider list."""
import json
from django.core.management.base import BaseCommand

from core.game_api_client import get_providers
from core.models import SuperSetting


class Command(BaseCommand):
    help = "Fetch game providers from external API (getProvider). Use --base-url or set game_api_url in SuperSetting."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            type=str,
            default=None,
            help="Base URL of game API (e.g. https://server.example.com). Overrides SuperSetting.",
        )
        parser.add_argument(
            "--output",
            type=str,
            choices=["json", "table"],
            default="table",
            help="Output format: json or table (default: table).",
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
        try:
            providers = get_providers(base_url)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"API error: {e}"))
            return
        if options["output"] == "json":
            self.stdout.write(json.dumps(providers, indent=2))
        else:
            if not providers:
                self.stdout.write("No providers returned.")
                return
            w_code = min(max((len(p.get("code", "")) for p in providers), default=0) + 1, 40)
            w_name = min(max((len(p.get("name", "")) for p in providers), default=0) + 1, 60)
            w_code = max(w_code, 6)
            w_name = max(w_name, 6)
            self.stdout.write(f"{'code':<{w_code}}  {'name':<{w_name}}")
            self.stdout.write("-" * (w_code + 2 + w_name))
            for p in providers:
                self.stdout.write(f"{p.get('code', ''):<{w_code}}  {p.get('name', ''):<{w_name}}")
        self.stdout.write(self.style.SUCCESS(f"Done. {len(providers)} provider(s)."))
