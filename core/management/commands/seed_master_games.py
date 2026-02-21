"""
Seed multiple game providers and games from docs/games (TXT + XLSX).
Uses get_or_create so runs are idempotent. Images from docs/games/<provider_slug>/ by game name or game_uid.
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
    provider_code_to_slug,
)

# docs/games relative to project root (parent of Django BASE_DIR)
DOCS_GAMES = Path(settings.BASE_DIR).parent / "docs" / "games"

# Row: (provider_code, provider_display_name, game_name, game_uid, category_or_none, image_folder_slug_or_none)
# image_folder_slug: used only for image lookup; when set (from XLSX filename), use it instead of provider_code for folders
GameRow = tuple[str, str, str, str, str | None, str | None]


def load_txt(docs_games: Path) -> list[GameRow]:
    """Load tab- or comma-separated TXT files. Columns: (index?), provider, name?, game_uid [, category]. Supports 2-col: provider, game_uid (name=uid)."""
    rows: list[GameRow] = []
    if not docs_games.exists():
        return rows
    for path in sorted(docs_games.glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.replace(",", "\t").split("\t")
            parts = [p.strip() for p in parts]
            if len(parts) >= 4:
                # index, provider, name, game_uid [, category]
                _idx, provider, name, game_uid = parts[0], parts[1], parts[2], parts[3]
                category = parts[4].strip() if len(parts) > 4 and parts[4] else None
                if provider and game_uid:
                    name = name or game_uid
                    code = provider_code_to_slug(provider)
                    display = provider.strip()[:255]
                    rows.append((code, display, name[:255], game_uid[:255], category[:255] if category else None, None))
            elif len(parts) == 2 and parts[0] and parts[1]:
                # provider, game_uid (e.g. lucksportsgaming.txt)
                provider, game_uid = parts[0], parts[1]
                code = provider_code_to_slug(provider)
                display = provider.strip()[:255]
                name = game_uid[:255]
                rows.append((code, display, name, game_uid[:255], None, None))
    return rows


def load_xlsx(docs_games: Path) -> list[GameRow]:
    """Load XLSX files; first row = header. Columns: Provider, Game (name), Game UID, Category (optional)."""
    rows: list[GameRow] = []
    try:
        import openpyxl
    except ImportError:
        return rows
    if not docs_games.exists():
        return rows
    for path in sorted(docs_games.glob("*.xlsx")):
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception:
            continue
        try:
            sheet = wb.active
            if not sheet:
                continue
            # First row = header
            header = [str(c.value or "").strip().lower() for c in sheet[1]]
            # Normalize column names: "game uid" / "game_uid" / "gameuid" etc.
            def col(name: str) -> int | None:
                for i, h in enumerate(header):
                    if name in h.replace(" ", "").replace("_", ""):
                        return i
                return None

            provider_col = None
            for key in ("provider", "providercode", "provider_code"):
                provider_col = col(key)
                if provider_col is not None:
                    break
            if provider_col is None:
                provider_col = 0
            game_col = None
            for key in ("game", "gamename", "name"):
                game_col = col(key)
                if game_col is not None:
                    break
            if game_col is None:
                game_col = 1
            uid_col = None
            for key in ("gameuid", "uid", "game_uid"):
                uid_col = col(key)
                if uid_col is not None:
                    break
            if uid_col is None:
                uid_col = 2
            category_col = None
            for key in ("category", "cat"):
                category_col = col(key)
                if category_col is not None:
                    break

            # Provider from filename if not in sheet
            file_provider_name = path.stem.strip()
            file_provider_code = provider_code_to_slug(file_provider_name)

            for row in sheet.iter_rows(min_row=2):
                values = [str(c.value or "").strip() for c in row]
                if uid_col is not None and uid_col < len(values) and values[uid_col]:
                    game_uid = values[uid_col][:255]
                else:
                    continue
                provider_name = (values[provider_col][:255] if provider_col < len(values) and values[provider_col] else file_provider_name) or file_provider_name
                provider_code = provider_code_to_slug(provider_name) if (provider_col < len(values) and values[provider_col]) else file_provider_code
                game_name = values[game_col][:255] if game_col < len(values) else ""
                if not game_name:
                    continue
                category = None
                if category_col is not None and category_col < len(values) and values[category_col]:
                    category = values[category_col][:255]
                # Use filename for image folder lookup so evolution_live/evolutionwebp etc. are found
                rows.append((provider_code, provider_name[:255], game_name, game_uid, category, file_provider_code))
        finally:
            wb.close()
    return rows


class Command(BaseCommand):
    help = (
        "Seed providers and games from docs/games (TXT + XLSX). Idempotent (get_or_create). "
        "Images from docs/games/<provider_slug>/ or <provider_slug>webp/ matched by game name or game_uid (partial match). "
        "Options: --dry-run, --fresh, --providers, --images-only."
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
            help="Delete all games and providers that would be seeded (from loaded data), then re-seed.",
        )
        parser.add_argument(
            "--providers",
            type=str,
            default="",
            help="Comma-separated provider codes to limit seeding (e.g. spribe,evolution_live).",
        )
        parser.add_argument(
            "--images-only",
            action="store_true",
            help="Only fill missing game images; do not create new games.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        fresh = options.get("fresh", False)
        providers_filter = [p.strip().lower() for p in (options.get("providers") or "").split(",") if p.strip()]
        images_only = options.get("images_only", False)

        docs_games = DOCS_GAMES
        if not docs_games.exists() and not dry_run:
            self.stdout.write(self.style.WARNING(f"docs/games path does not exist: {docs_games}"))

        # Load all rows
        all_rows: list[GameRow] = []
        all_rows.extend(load_txt(docs_games))
        all_rows.extend(load_xlsx(docs_games))

        if not all_rows:
            self.stdout.write(self.style.WARNING("No game rows loaded from docs/games (TXT or XLSX)."))
            return

        if providers_filter:
            all_rows = [r for r in all_rows if r[0].lower() in providers_filter]
            if not all_rows:
                self.stdout.write(self.style.WARNING(f"No rows left after filtering by providers: {providers_filter}"))
                return

        # --fresh: delete all games and providers that we are about to seed
        if fresh and not dry_run and not images_only:
            provider_codes = list({r[0] for r in all_rows})
            for code in provider_codes:
                provider = GameProvider.objects.filter(code=code).first()
                if provider:
                    deleted_games, _ = Game.objects.filter(provider=provider).delete()
                    provider.delete()
                    self.stdout.write(self.style.WARNING(f"Fresh: deleted provider {code} and {deleted_games} games."))

        zero = Decimal("0")
        created_providers = 0
        created_categories = 0
        created_games = 0
        skipped_games = 0
        images_set = 0

        # Distinct providers first (by code)
        seen_providers: dict[str, str] = {}
        for provider_code, provider_name, _gn, _uid, _cat, _img in all_rows:
            if provider_code not in seen_providers:
                seen_providers[provider_code] = provider_name

        if not dry_run and not images_only:
            for code, name in seen_providers.items():
                _, created = GameProvider.objects.get_or_create(
                    code=code,
                    defaults={"name": name, "is_active": True},
                )
                if created:
                    created_providers += 1

        for provider_code, _provider_name, game_name, game_uid, category_name, image_folder_slug in all_rows:
            if dry_run:
                created_games += 1
                continue

            provider = GameProvider.objects.filter(code=provider_code).first()
            if not provider:
                if images_only:
                    continue
                provider, _ = GameProvider.objects.get_or_create(
                    code=provider_code,
                    defaults={"name": seen_providers.get(provider_code, provider_code), "is_active": True},
                )
                created_providers += 1

            cat_name = (category_name or infer_category(game_name))[:255]
            category, cat_created = GameCategory.objects.get_or_create(
                name=cat_name,
                defaults={"is_active": True},
            )
            if cat_created:
                created_categories += 1

            if images_only:
                game = Game.objects.filter(provider=provider, game_uid=game_uid).first()
                if game and not game.image:
                    slug_for_images = image_folder_slug if image_folder_slug is not None else provider_code
                    folder_candidates = get_image_folder_candidates(docs_games, slug_for_images)
                    path = find_image_for_game_in_folders(folder_candidates, game_name, game_uid)
                    if path:
                        with open(path, "rb") as f:
                            game.image.save(path.name, ContentFile(f.read()), save=True)
                        images_set += 1
                continue

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

            # Set image when created or missing (use XLSX filename slug for folder when available)
            if game_created or not game.image:
                slug_for_images = image_folder_slug if image_folder_slug is not None else provider_code
                folder_candidates = get_image_folder_candidates(docs_games, slug_for_images)
                path = find_image_for_game_in_folders(folder_candidates, game_name, game_uid)
                if path:
                    try:
                        with open(path, "rb") as f:
                            game.image.save(path.name, ContentFile(f.read()), save=True)
                        images_set += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Could not save image for {game_name!r}: {e}"))

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run: would create {created_games} games (and providers/categories as needed)."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Providers: {created_providers} created. Categories: {created_categories} created. "
                    f"Games: {created_games} created, {skipped_games} skipped. Images set: {images_set}."
                )
            )
