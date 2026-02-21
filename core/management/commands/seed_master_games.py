"""
Seed only allowed providers and their games from docs/games (TXT, XLSX, and JILI).
Providers: spribe, sexy gaming, smart soft gaming, saba sports, pragmatic live, luck sport gaming, evo play asia, evolution live, jili.
Uses get_or_create so runs are idempotent. Images from docs/games (e.g. jiliwebp, spribe, evolutionwebp).
--full-reset: delete all Game, GameCategory, GameProvider then re-seed (providers first, then categories, then games with images).
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

# Only these providers are seeded (slug form). Games come only from files under docs/games for these.
ALLOWED_PROVIDER_SLUGS = frozenset({
    "spribe",
    "sexy_gaming",
    "smartsoft_gaming",
    "saba_sports",
    "pragmatic_live",
    "lucksportsgaming",
    "lucksportgaming",  # e.g. LuckSportGaming in TXT
    "evoplay_asia",
    "evolution_live",
    "jili",
})

# docs/games relative to project root (parent of Django BASE_DIR)
DOCS_GAMES = Path(settings.BASE_DIR).parent / "docs" / "games"

# Row: (provider_code, provider_display_name, game_name, game_uid, category_or_none, image_folder_slug_or_none)
# image_folder_slug: used only for image lookup; when set (from XLSX filename), use it instead of provider_code for folders
GameRow = tuple[str, str, str, str, str | None, str | None]


def load_txt(docs_games: Path) -> list[GameRow]:
    """Load tab- or comma-separated TXT files for allowed providers only. Columns: (index?), provider, name?, game_uid [, category]. Supports 2-col: provider, game_uid."""
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
                _idx, provider, name, game_uid = parts[0], parts[1], parts[2], parts[3]
                category = parts[4].strip() if len(parts) > 4 and parts[4] else None
                if provider and game_uid:
                    name = name or game_uid
                    code = provider_code_to_slug(provider)
                    if code not in ALLOWED_PROVIDER_SLUGS:
                        continue
                    if code == "lucksportgaming":
                        code = "lucksportsgaming"
                    display = provider.strip()[:255]
                    rows.append((code, display, name[:255], game_uid[:255], category[:255] if category else None, None))
            elif len(parts) == 2 and parts[0] and parts[1]:
                provider, game_uid = parts[0], parts[1]
                code = provider_code_to_slug(provider)
                if code not in ALLOWED_PROVIDER_SLUGS:
                    continue
                if code == "lucksportgaming":
                    code = "lucksportsgaming"
                display = provider.strip()[:255]
                name = game_uid[:255]
                rows.append((code, display, name, game_uid[:255], None, None))
    return rows


def load_xlsx(docs_games: Path) -> list[GameRow]:
    """Load XLSX files for allowed providers only. First row = header. Provider = filename (Evolution live, Sexy Gaming, etc.)."""
    rows: list[GameRow] = []
    try:
        import openpyxl
    except ImportError:
        return rows
    if not docs_games.exists():
        return rows
    for path in sorted(docs_games.glob("*.xlsx")):
        file_provider_name = path.stem.strip()
        file_provider_code = provider_code_to_slug(file_provider_name)
        if file_provider_code not in ALLOWED_PROVIDER_SLUGS:
            continue
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception:
            continue
        try:
            sheet = wb.active
            if not sheet:
                continue
            header = [str(c.value or "").strip().lower() for c in sheet[1]]
            def col(name: str) -> int | None:
                for i, h in enumerate(header):
                    if name in h.replace(" ", "").replace("_", ""):
                        return i
                return None

            provider_col = 0
            game_col = col("game") or col("gamename") or col("name") or 1
            uid_col = col("gameuid") or col("uid") or col("game_uid") or 2
            category_col = col("category") or col("cat")

            for row in sheet.iter_rows(min_row=2):
                values = [str(c.value or "").strip() for c in row]
                if uid_col >= len(values) or not values[uid_col]:
                    continue
                game_uid = values[uid_col][:255]
                game_name = (values[game_col][:255] if game_col < len(values) else "") or ""
                if not game_name:
                    continue
                category = None
                if category_col is not None and category_col < len(values) and values[category_col]:
                    category = values[category_col][:255]
                # Always use filename as provider so we only have these 8 + jili
                rows.append((file_provider_code, file_provider_name[:255], game_name, game_uid, category, file_provider_code))
        finally:
            wb.close()
    return rows


def load_jili(docs_games: Path) -> list[GameRow]:
    """Load JILI games from seed_jili_games list. Images from docs/games/jiliwebp."""
    from core.management.commands.seed_jili_games import JILI_GAMES
    rows: list[GameRow] = []
    for name, game_uid in JILI_GAMES:
        name = (name or "").strip()[:255]
        game_uid = (game_uid or "").strip()[:255]
        if not game_uid:
            continue
        rows.append(("jili", "JILI", name, game_uid, None, "jili"))
    return rows


# JILI provider launch config (from seed_jili_provider)
JILI_API_ENDPOINT = "https://allapi.online/launch_game1_js"
JILI_API_SECRET = "4d45bba519ac2d39d1618f57120b84b7"
JILI_API_TOKEN = "184de030-912d-4c26-81fc-6c5cd3c05add"


class Command(BaseCommand):
    help = (
        "Seed only allowed providers (spribe, sexy gaming, smart soft, saba sports, pragmatic live, luck sport, evoplay asia, evolution live, jili) from docs/games. "
        "Includes JILI games and launch config. --full-reset: delete all Game, GameCategory, GameProvider then re-seed (providers, then categories, then games with images)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be created; no DB writes.",
        )
        parser.add_argument(
            "--full-reset",
            action="store_true",
            help="Delete ALL games, game categories, and game providers; then re-seed (providers first, then categories, then games with images).",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete only the providers/games that would be seeded (from loaded data), then re-seed.",
        )
        parser.add_argument(
            "--providers",
            type=str,
            default="",
            help="Comma-separated provider codes to limit seeding (e.g. spribe,evolution_live,jili).",
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

        # Load all rows (only allowed providers; JILI from seed_jili_games list)
        all_rows: list[GameRow] = []
        all_rows.extend(load_txt(docs_games))
        all_rows.extend(load_xlsx(docs_games))
        all_rows.extend(load_jili(docs_games))

        if not all_rows:
            self.stdout.write(self.style.WARNING("No game rows loaded from docs/games (TXT, XLSX, or JILI)."))
            return

        if providers_filter:
            all_rows = [r for r in all_rows if r[0].lower() in providers_filter]
            if not all_rows:
                self.stdout.write(self.style.WARNING(f"No rows left after filtering by providers: {providers_filter}"))
                return

        # --full-reset: delete ALL games, categories, providers then re-seed
        if options.get("full_reset") and not dry_run and not images_only:
            game_count, _ = Game.objects.all().delete()
            cat_count, _ = GameCategory.objects.all().delete()
            prov_count, _ = GameProvider.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Full reset: deleted {game_count} games, {cat_count} categories, {prov_count} providers."))

        # --fresh: delete only providers/games that we are about to seed
        if fresh and not dry_run and not images_only and not options.get("full_reset"):
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
                defaults = {"name": name, "is_active": True}
                if code == "jili":
                    defaults["api_endpoint"] = JILI_API_ENDPOINT
                    defaults["api_secret"] = JILI_API_SECRET
                    defaults["api_token"] = JILI_API_TOKEN
                _, created = GameProvider.objects.get_or_create(
                    code=code,
                    defaults=defaults,
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
                    folder_candidates = list(get_image_folder_candidates(docs_games, slug_for_images))
                    if provider_code == "jili":
                        folder_candidates.append(Path(settings.BASE_DIR) / "jiliwebp")
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
                folder_candidates = list(get_image_folder_candidates(docs_games, slug_for_images))
                if provider_code == "jili":
                    folder_candidates.append(Path(settings.BASE_DIR) / "jiliwebp")
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
