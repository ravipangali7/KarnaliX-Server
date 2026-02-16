"""Fetch all providers and their games from external API and seed GameProvider, GameCategory, Game."""
from django.core.management.base import BaseCommand

from core.game_api_client import get_providers, get_provider_games
from core.models import SuperSetting, GameProvider, GameCategory, Game


class Command(BaseCommand):
    help = (
        "Fetch getProvider + providerGame for each provider and upsert GameProvider, "
        "GameCategory, Game. Use --base-url or SuperSetting. Optional --dry-run to only fetch and print."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            type=str,
            default=None,
            help="Base URL of game API. Overrides SuperSetting.",
        )
        parser.add_argument(
            "--count-per-provider",
            type=int,
            default=500,
            help="Max games to fetch per provider (default: 500).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only fetch and print; do not write to DB.",
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
        count_per_provider = options["count_per_provider"]
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no DB writes."))
        try:
            providers = get_providers(base_url)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"getProvider error: {e}"))
            return
        if not providers:
            self.stdout.write("No providers returned from API.")
            return
        self.stdout.write(f"Found {len(providers)} provider(s).")
        created_providers = 0
        created_categories = 0
        created_games = 0
        updated_games = 0
        default_category_name = "Other"
        for prov in providers:
            code = prov.get("code") or ""
            name = prov.get("name") or code
            if not code:
                continue
            if not dry_run:
                gp, created = GameProvider.objects.get_or_create(
                    code=code,
                    defaults={"name": name},
                )
                if created:
                    created_providers += 1
                else:
                    if gp.name != name:
                        gp.name = name
                        gp.save(update_fields=["name"])
            else:
                gp = None
            try:
                games = get_provider_games(base_url, code, count=count_per_provider)
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"providerGame({code}) error: {e}"))
                continue
            self.stdout.write(f"  {code}: {len(games)} game(s)")
            seen_categories = set()
            for g in games:
                game_name = (g.get("game_name") or "").strip()
                game_code = (g.get("game_code") or "").strip()
                game_type = (g.get("game_type") or "").strip() or default_category_name
                game_image = (g.get("game_image") or "").strip()
                if not game_code:
                    continue
                if dry_run:
                    continue
                cat_name = game_type[:255] if game_type else default_category_name
                if cat_name not in seen_categories:
                    cat, cat_created = GameCategory.objects.get_or_create(
                        name=cat_name,
                        defaults={"is_active": True},
                    )
                    if cat_created:
                        created_categories += 1
                    seen_categories.add(cat_name)
                else:
                    cat = GameCategory.objects.get(name=cat_name)
                game_uid = game_code
                defaults = {
                    "name": game_name[:255] or game_uid,
                    "category": cat,
                    "image_url": game_image or None,
                    "is_active": True,
                }
                obj, created = Game.objects.update_or_create(
                    provider=gp,
                    game_uid=game_uid,
                    defaults=defaults,
                )
                if created:
                    created_games += 1
                else:
                    updated_games += 1
        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Providers: +{created_providers}, Categories: +{created_categories}, "
                f"Games: +{created_games} created, {updated_games} updated."
            )
        )
