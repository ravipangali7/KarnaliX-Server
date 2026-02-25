"""
Seed Ezugi provider and its games (embedded list). Images from docs/games/ezugiwebp (filenames match game name).
Uses get_or_create so runs are idempotent. --fresh: delete only Ezugi games and re-seed.
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

# Provider: code and display name
EZUGI_PROVIDER_CODE = "ezugi"
EZUGI_PROVIDER_NAME = "Ezugi"

# docs/games relative to project root (parent of Django BASE_DIR)
DOCS_GAMES = Path(settings.BASE_DIR).parent / "docs" / "games"
IMAGE_FOLDER_SLUG = "ezugi"  # -> ezugiwebp via get_image_folder_candidates

# (game_name, game_uid)
EZUGI_GAMES = [
    ("Blackjack C", "cd0e742af59d62f2241c1f6bc19954c5"),
    ("Blackjack B", "90bd51cc8cde4d06bbb6ae787c8c3eb3"),
    ("EZ Dealer Roleta Brazileira", "4165dec80667c631a66941c68a5bee96"),
    ("Roleta da sorte", "eacbc601b30b2992db7c3eda2a777fe6"),
    ("Dragon Tiger da Sorte", "f84c5ce9ae53fac2e7afa9f8157e453c"),
    ("Blackjack A", "d9fc983ad1ac44e2a6365ae6cc5c9762"),
    ("Blackjack da Sorte", "4f22281594a261d99c1b1222bc2d3a8a"),
    ("Oracle 360 Roulette", "c74c90c712566b3212cd08a4c191275d"),
    ("Oracle Real Roulette", "c5d4fd6cec78dd439ed2ee33c8965777"),
    ("Russian Roulette", "ce1b314dccf3756a581d117190ddd172"),
    ("Turkish Roulette", "f8bbea8c1a3b2204190d6a7e3c8d55e8"),
    ("EZ Dealer Roulette Mandarin", "db62931938bcaf0b327b11304a406b16"),
    ("EZ Dealer Roulette Japanese", "4a963476f45508711a7147ba888600ad"),
    ("EZ Roulette", "fb53959d1f55434d555ee50e0fc764b8"),
    ("Fiesta Roulette", "4e94d574914b472cb4ecc4f3c05647d4"),
    ("Ruleta del Sol", "4589bec2f464797bb0752d2eb283babd"),
    ("Spanish Roulette", "7d0d91d4477b9d14e3a4ba40e34451ea"),
    ("Casino Marina Roulette 2", "44b99989a409c0ca24aca784f0433dcc"),
    ("Casino Marina Roulette 1", "d205c518208016404504e995620d2b83"),
    ("Ultimate Andar Bahar", "75f81c56555d394503f544f3431ef370"),
    ("Teen Patti 3 Card", "26f9f76a8fc813b8abcb6b8cb03c2eab"),
    ("Namaste Roulette", "b1ffb1afd5b76785bd4ee21e31400849"),
    ("Prestige Auto Roulette", "efaed662fbebbb84e056c09580ae1aa4"),
    ("Diamond Roulette", "a40c7e3222a17717bcc1d2e4f5d6eae8"),
    ("Speed Auto Roulette", "f4299915859041e94b641a558a1ca9df"),
    ("Speed Roulette", "b5c8e49fdd80b57de6da0e234b1bd683"),
    ("Fiesta Baccarat", "66a525d29fdfb01af4335ceabfb0cad2"),
    ("Casino Marina Baccarat 4", "527db204952a306f8459b9d702dfb285"),
    ("Casino Marina Baccarat 3", "243c511540c8d82597245bd282c327a1"),
    ("Casino Marina Baccarat 2", "58501dadbf6088c4722e72660a1f38b7"),
    ("Turkish Unlimited Blackjack", "5b66adfdde56956cf3d4273acfad99d4"),
    ("Fiesta Unlimited Blackjack", "5255de9f809be3a1515cf28095a95039"),
    ("Spanish Unlimited Blackjack", "e34d828be9c5dbd861dbcc414d2daad7"),
    ("Turkish Blackjack 3", "7b4f503301dd3fbbb0beb71b814452c9"),
    ("Russian Blackjack 2", "716e3dd6a3e560067425fec4951abe25"),
    ("Russian Blackjack 1", "4244969212746e76beb92f71ba300114"),
    ("Turkish Blackjack 2", "25384176a2560a0a69c301b1c8cf83f9"),
    ("Turkish Blackjack 1", "9e8ce809e74cc1ebda5ca59a927def6b"),
    ("Rumba Blackjack 4", "1c77a06449c384b97f6239572ef87be3"),
    ("Rumba Blackjack 3", "e6a2e3cc081f28298164d9197c38ec7c"),
    ("Rumba Blackjack 2", "22c57f788355265137a61874d0b53bb9"),
    ("Rumba Blackjack 1", "8ef17e9b4c5c67b7f43f4bced3c31a27"),
    ("VIP Diamond Blackjack", "48420430ede7a5d7615dae19aa4463a7"),
    ("Surrender Blackjack", "d9723621d4007265d66cc115b5a953df"),
    ("Gold Blackjack 6", "9353bede98efba162ed5b04534e9ac00"),
    ("Blackjack 7", "3ab6fd647eac8e687af18ce5bceadfa5"),
    ("Romanian Blackjack", "7a45bdcb14c3e1eefb0dcf91668d88ee"),
    ("Gold Blackjack 1", "2955688bdb4f23686e3ce61b905aafeb"),
    ("Gold Blackjack 3", "02478a653aa641470951d0a9cae59699"),
    ("Blackjack 1", "753fd4063959abf96f927fe171632d47"),
    ("VIP No Commission Speed Cricket Baccarat", "5619183cf03c3b03ebd01bbf42b37de4"),
    ("VIP Fortune Baccarat", "044a24737767690ed7a0be43ed9dd137"),
    ("Speed Fortune Baccarat", "a4f20ded65fffacd9001782619a90cce"),
    ("Fortune Baccarat", "04f266b7a2e9e68865d52fb7f2ac5e8a"),
    ("Speed Cricket Baccarat", "928af567b0839c6496bbfbb5709c5014"),
    ("Platinum Blackjack 1", "257b58d4471d0ea234380c10b145915f"),
    ("Gold Blackjack 4", "a75308c716157fde9e4faf84bcf80f1f"),
    ("Video Blackjack", "c9e306299b99ad529789673a6b4a8b88"),
    ("Unlimited Blackjack", "18cf7864fee424c7471bb7996aa4d37a"),
    ("Ultimate Sic Bo", "5cd59a9381764a84f5792d237469903a"),
    ("Sic Bo", "101e3c281b35485001bec47561a0a03e"),
    ("Russian Poker", "31ee0411b49acf83932fa0519e676997"),
    ("Italian Roulette", "2e31c310ad2491d3c6021f6063dc9b74"),
    ("EZ Dealer Roulette Thai", "a987ab0cda923c2f8e6fbc5292d7a062"),
    ("Portomaso Roulette 2", "91a2daa3d4b8065ffb75818568907ff8"),
    ("Casino Marina Baccarat 1", "2227c0b7445885e9f6a852eaf2fe74b6"),
    ("Casino Marina Andar Bahar", "5058f0aa42547208b1307fcbf21dcf9a"),
    ("One Day Teen Patti", "01556a46c5163d5570739dd7cddfcf68"),
    ("No Commission Baccarat", "958d30b26401872450a74a2d710adef6"),
    ("Lucky 7", "c88c40ec4fc544518d938315e2d1b2a3"),
    ("Dragon Tiger", "efdb52994fbfe97efcbd878dbd697ebb"),
    ("Cricket War", "93e289d1b18a9f82fb5d790f3c8e6735"),
    ("Casino Hold'em", "045e21f65e0e96eb502a4856ca9ababb"),
    ("Salon Prive Blackjack", "9f944a6cb336df7664f81e3ff6aba50e"),
    ("Gold Blackjack 5", "b307868469ec2b2e612045335086ff33"),
    ("Bet on Teen Patti", "e1b5650cd867be7719c15e7596aa7217"),
    ("Bet On Numbers HD", "531bac2b5726f8d9249eb5b0d432cb97"),
    ("Super 6 Baccarat", "f1fa68fce40959ce6ad5f367739f9e27"),
    ("Knockout Baccarat", "b12517092523e6d4b0c991a181c7d813"),
    ("Baccarat", "add11b218177a9898c594233148ca740"),
    ("Auto Roulette", "9b8fae325d15021b79f4fc650d5b8df5"),
    ("Andar Bahar", "435b892a73bf466e0ad584d480e12143"),
    ("32 Cards", "69e690d4f810d033fb4bb8ac7f3cc12f"),
    ("Ezugi Lobby", "d0e052b031dfcdb08d1803f4bcc618ef"),
]


class Command(BaseCommand):
    help = (
        "Seed Ezugi provider and games from embedded list. "
        "Images from docs/games/ezugiwebp. --fresh: delete Ezugi games and re-seed."
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
            help="Delete existing Ezugi games (and provider if no other games use it), then re-seed.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        fresh = options.get("fresh", False)

        games_data = [(name[:255], uid[:255]) for name, uid in EZUGI_GAMES if name and uid]
        if not games_data:
            self.stdout.write(self.style.WARNING("No Ezugi games defined."))
            return

        docs_games = DOCS_GAMES
        folder_candidates = list(get_image_folder_candidates(docs_games, IMAGE_FOLDER_SLUG))
        if not dry_run and not any(p.exists() for p in folder_candidates):
            self.stdout.write(
                self.style.WARNING(
                    f"Image folder not found (tried: {[str(p) for p in folder_candidates]}). Images will be skipped."
                )
            )

        # --fresh: remove existing Ezugi provider and its games
        if fresh and not dry_run:
            provider = GameProvider.objects.filter(code=EZUGI_PROVIDER_CODE).first()
            if provider:
                deleted, _ = Game.objects.filter(provider=provider).delete()
                provider.delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"Fresh: deleted provider '{EZUGI_PROVIDER_NAME}' and {deleted} games."
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
                code=EZUGI_PROVIDER_CODE,
                defaults={"name": EZUGI_PROVIDER_NAME, "is_active": True},
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
                    f"Dry run: would create {len(games_data)} games for Ezugi (and provider/categories as needed)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Ezugi: provider created={created_provider}, categories created={created_categories}, "
                    f"games created={created_games}, skipped={skipped_games}, images set={images_set}."
                )
            )
