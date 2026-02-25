"""
Seed Sexy Gaming provider and its games from docs/games/Sexy Gaming.xlsx (game name, uid).
Images from docs/games/sexygamingwebp (filenames match game name).
Uses get_or_create so runs are idempotent. --fresh: delete only Sexy Gaming games and re-seed.
"""
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.models import Game, GameCategory, GameProvider
from core.management.utils import (
    find_image_for_game_in_folders,
    get_image_folder_candidates,
    infer_category,
)

# Provider: code and display name (must match existing/provider lookup)
SEXY_GAMING_PROVIDER_CODE = "sexy_gaming"
SEXY_GAMING_PROVIDER_NAME = "Sexy Gaming"

# docs/games relative to project root (parent of Django BASE_DIR)
DOCS_GAMES = Path(settings.BASE_DIR).parent / "docs" / "games"
SEXY_GAMING_XLSX = DOCS_GAMES / "Sexy Gaming.xlsx"
IMAGE_FOLDER_SLUG = "sexy_gaming"  # -> sexygamingwebp via get_image_folder_candidates


def load_sexy_gaming_xlsx(path: Path) -> list[tuple[str, str]]:
    """Load (game_name, game_uid) from Sexy Gaming.xlsx. No header: col 0 = game name, col 1 = uid."""
    rows: list[tuple[str, str]] = []
    if not path.exists():
        return rows
    try:
        import openpyxl
    except ImportError:
        return rows
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception:
        return rows
    try:
        sheet = wb.active
        if not sheet:
            return rows
        # First column = game name, second column = uid (no header row)
        for row in sheet.iter_rows(min_row=1):
            values = [str(c.value or "").strip() for c in row]
            if len(values) < 2 or not values[1]:
                continue
            game_name = values[0][:255] if values[0] else ""
            game_uid = values[1][:255]
            if not game_name:
                continue
            rows.append((game_name, game_uid))
    finally:
        wb.close()
    return rows


class Command(BaseCommand):
    help = (
        "Seed Sexy Gaming provider and games from docs/games/Sexy Gaming.xlsx (game name, uid). "
        "Images from docs/games/sexygamingwebp. --fresh: delete Sexy Gaming games and re-seed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be created; no DB writes.",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing Sexy Gaming games (and provider if no other games use it), then re-seed.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        fresh = options.get("fresh", False)

        games_data = load_sexy_gaming_xlsx(SEXY_GAMING_XLSX)
        if not games_data:
            self.stdout.write(
                self.style.WARNING(
                    f"No rows loaded from {SEXY_GAMING_XLSX}. Ensure file exists with col 0 = game name, col 1 = uid (no header)."
                )
            )
            return

        docs_games = DOCS_GAMES
        folder_candidates = list(get_image_folder_candidates(docs_games, IMAGE_FOLDER_SLUG))
        if not dry_run and not any(p.exists() for p in folder_candidates):
            self.stdout.write(
                self.style.WARNING(
                    f"Image folder not found (tried: {[str(p) for p in folder_candidates]}). Images will be skipped."
                )
            )

        # --fresh: remove existing Sexy Gaming provider and its games
        if fresh and not dry_run:
            provider = GameProvider.objects.filter(code=SEXY_GAMING_PROVIDER_CODE).first()
            if provider:
                deleted, _ = Game.objects.filter(provider=provider).delete()
                provider.delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"Fresh: deleted provider '{SEXY_GAMING_PROVIDER_NAME}' and {deleted} games."
                    )
                )

        zero = Decimal("0")
        created_provider = 0
        created_categories = 0
        created_games = 0
        skipped_games = 0
        images_set = 0

        if not dry_run:
            provider, created = GameProvider.objects.get_or_create(
                code=SEXY_GAMING_PROVIDER_CODE,
                defaults={"name": SEXY_GAMING_PROVIDER_NAME, "is_active": True},
            )
            if created:
                created_provider += 1
        else:
            provider = None

        for game_name, game_uid in games_data:
            if dry_run:
                created_games += 1
                continue

            cat_name = infer_category(game_name)[:255]
            category, cat_created = GameCategory.objects.get_or_create(
                name=cat_name,
                defaults={"is_active": True},
            )
            if cat_created:
                created_categories += 1

            game, game_created = Game.objects.get_or_create(
                provider=provider,
                game_uid=game_uid,
                defaults={
                    "name": game_name,
                    "category": category,
                    "is_active": True,
                    "min_bet": zero,
                    "max_bet": zero,
                },
            )
            if game_created:
                created_games += 1
            else:
                skipped_games += 1

            if game_created or not game.image:
                path = find_image_for_game_in_folders(folder_candidates, game_name, game_uid)
                if path:
                    try:
                        with open(path, "rb") as f:
                            game.image.save(path.name, ContentFile(f.read()), save=True)
                        images_set += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"Could not save image for {game_name!r}: {e}")
                        )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run: would create {len(games_data)} games for Sexy Gaming (and provider/categories as needed)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sexy Gaming: provider created={created_provider}, categories created={created_categories}, "
                    f"games created={created_games}, skipped={skipped_games}, images set={images_set}."
                )
            )
