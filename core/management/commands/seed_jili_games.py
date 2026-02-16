"""Seed JILI provider with games (name + game_uid), image_url from jiliwebp base, category inferred from name."""
from decimal import Decimal

from django.core.management.base import BaseCommand

from core.models import Game, GameCategory, GameProvider

# Base URL for game images (e.g. jiliwebp CDN); adjust to real URL as needed.
JILI_IMAGE_BASE = "https://cdn.example.com/jiliwebp"


def infer_category(name: str) -> str:
    """Infer category from game name. Returns category name (max 255 chars)."""
    n = (name or "").strip()
    n_lower = n.lower()
    if "fishing" in n_lower:
        return "Fishing"
    if "bingo" in n_lower:
        return "Bingo"
    if "roulette" in n_lower:
        return "Roulette"
    if "keno" in n_lower:
        return "Keno"
    if "crash" in n_lower:
        return "Crash"
    table_keywords = (
        "baccarat", "blackjack", "poker", "teen patti", "teenpatti", "andar bahar",
        "rummy", "ludo", "callbreak", "tongits", "pusoy", "caribbean", "texas hold",
        "sic bo", "video poker", "stud poker", "mini flush", "pool rummy", "ak47",
        "jhandi munda", "fish prawn crab", "speed baccarat", "sabong", "e-sabong",
    )
    for kw in table_keywords:
        if kw in n_lower:
            return "Live Casino"
    return "Slot"


# (name, game_uid) - JILI games list
JILI_GAMES = [
    ("Royal Fishing", "e794bf5717aca371152df192341fe68b"),
    ("Bombing Fishing", "e333695bcff28acdbecc641ae6ee2b23"),
    ("Dinosaur Tycoon", "eef3e28f0e3e7b72cbca61e7924d00f1"),
    ("Jackpot Fishing", "3cf4a85cb6dcf4d8836c982c359cd72d"),
    ("Dragon Fortune", "1200b82493e4788d038849bca884d773"),
    ("Mega Fishing", "caacafe3f64a6279e10a378ede09ff38"),
    ("Boom Legend", "f02ede19c5953fce22c6098d860dadf4"),
    ("Happy Fishing", "71c68a4ddb63bdc8488114a08e603f1c"),
    ("All-star Fishing", "9ec2a18752f83e45ccedde8dfeb0f6a7"),
    ("Dinosaur Tycoon II", "bbae6016f79f3df74e453eda164c08a4"),
    ("Ocean King Jackpot", "564c48d53fcddd2bcf0bf3602d86c958"),
    ("Chin Shi Huang", "24da72b49b0dd0e5cbef9579d09d8981"),
    ("God Of Martial", "21ef8a7ddd39836979170a2e7584e333"),
    ("Hot Chilli", "c845960c81d27d7880a636424e53964d"),
    ("Fortune Tree", "6a7e156ceec5c581cd6b9251854fe504"),
    ("War Of Dragons", "4b1d7ffaf9f66e6152ea93a6d0e4215b"),
    ("Gem Party", "756cf3c73a323b4bfec8d14864e3fada"),
    ("Lucky Ball", "893669898cd25d9da589a384f1d004df"),
    ("Hyper Burst", "a47b17970036b37c1347484cf6956920"),
    ("Shanghai Beauty", "795d0cae623cbf34d7f1aa93bbcded28"),
    ("Fa Fa Fa", "54c41adcf43fdb6d385e38bc09cd77ca"),
    ("Candy Baby", "2cc3b68cbcfacac2f7ef2fe19abc3c22"),
    ("Hawaii Beauty", "6409b758471b6df30c6b137b49f4d92e"),
    ("SevenSevenSeven", "61d46add6841aad4758288d68015eca6"),
    ("Bubble Beauty", "a78d2ed972aab8ba06181cc43c54a425"),
    ("FortunePig", "8488c76ee2afb8077fbd7eec62721215"),
    ("Crazy777", "8c62471fd4e28c084a61811a3958f7a1"),
    ("Bao boon chin", "8c4ebb3dc5dcf7b7fe6a26d5aadd2c3d"),
    ("Night City", "78e29705f7c6084114f46a0aeeea1372"),
    ("Fengshen", "09699fd0de13edbb6c4a194d7494640b"),
    ("Crazy FaFaFa", "a57a8d5176b54d4c825bd1eee8ab34df"),
    ("XiYangYang", "5a962d0e31e0d4c0798db5f331327e4f"),
    ("DiamondParty", "48d598e922e8c60643218ccda302af08"),
    ("Golden Bank", "c3f86b78938eab1b7f34159d98796e88"),
    ("Dragon Treasure", "c6955c14f6c28a6c2a0c28274fec7520"),
    ("Charge Buffalo", "984615c9385c42b3dad0db4a9ef89070"),
    ("Lucky Goldbricks", "d84ef530121953240116e3b2e93f6af4"),
    ("Super Ace", "bdfb23c974a2517198c5443adeea77a8"),
    ("Money Coming", "db249defce63610fccabfa829a405232"),
    ("Golden Queen", "8de99455c2f23f6827666fd798eb80ef"),
    ("Jungle King", "4db0ec24ff55a685573c888efed47d7f"),
    ("Monkey Party", "fd369a4a7486ff303beea267ec5c8eff"),
    ("Boxing King", "981f5f9675002fbeaaf24c4128b938d7"),
    ("Secret Treasure", "1d1f267e3a078ade8e5ccd56582ac94f"),
    ("Pharaoh Treasure", "c7a69ab382bd1ff0e6eb65b90a793bdd"),
    ("Lucky Coming", "ba858ec8e3b5e2b4da0d16b3a2330ca7"),
    ("Super Rich", "b92f491a63ac84b106b056e9d46d35c5"),
    ("RomaX", "e5ff8e72418fcc608d72ea21cc65fb70"),
    ("Golden Empire", "490096198e28f770a3f85adb6ee49e0f"),
    ("Fortune Gems", "a990de177577a2e6a889aaac5f57b429"),
    ("Crazy Hunter", "69082f28fcd46cbfd10ce7a0051f24b6"),
    ("Party Night", "d505541d522aa5ca01fc5e97cfcf2116"),
    ("Magic Lamp", "582a58791928760c28ec4cef3392a49f"),
    ("Agent Ace", "8a4b4929e796fda657a2d38264346509"),
    ("TWIN WINS", "c74b3cbda5d16f77523e41c25104e602"),
    ("Ali Baba", "cc686634b4f953754b306317799f1f39"),
    ("Mega Ace", "eba92b1d3abd5f0d37dfbe112abdf0e2"),
    ("Medusa", "2c17b7c4e2ce5b8bebf4bd10e3e958d7"),
    ("Book of Gold", "6b283c434fd44250d83b7c2420f164f9"),
    ("Thor X", "7e6aa773fa802aaa9cb1f2fac464736e"),
    ("Happy Taxi", "1ed896aae4bdc78c984021307b1dd177"),
    ("Gold Rush", "2a5d731e0fd60f52873a24ece11f2c0b"),
    ("Mayan Empire", "5c2383ef253f9c36dacec4b463d61622"),
    ("Crazy Pusher", "00d92d5cec10cf85623938222a6c2bb6"),
    ("Bone Fortune", "aab3048abc6a88e0759679fbe26e6a8d"),
    ("JILI CAISHEN", "11e330c2b23f106815f3b726d04e4316"),
    ("Bonus Hunter", "39775cdc4170e56c5f768bdee8b4fa00"),
    ("World Cup", "28374b7ad7c91838a46404f1df046e5a"),
    ("Samba", "6d35789b2f419c1db3926350d57c58d8"),
    ("Neko Fortune", "9a391758f755cb30ff973e08b2df6089"),
    ("Wild Racer", "2f0c5f96cda3c6e16b3929dd6103df8e"),
    ("Pirate Queen", "70999d5bcf2a1d1f1fb8c82e357317f4"),
    ("Golden Joker", "f301fe0b22d1540b1f215d282b20c642"),
    ("Wild Ace", "9a3b65e2ae5343df349356d548f3fc4b"),
    ("Master Tiger", "d2b48fe98ac2956eeefd2bc4f7e0335a"),
    ("Fortune Gems 2", "664fba4da609ee82b78820b1f570f4ad"),
    ("Sweet Land", "91250a55f75a3c67ed134b99bf587225"),
    ("Cricket King 18", "dcf220f4e3ecca0278911a55e6f11c77"),
    ("Elf Bingo", "5cec2b309a8845b38f8e9b4e6d649ea2"),
    ("Cricket Sah 75", "6720a0ce1d06648ff390fbea832798a9"),
    ("Golden Temple", "976c5497256c020ac012005f6bb166ad"),
    ("Devil Fire", "1b4c5865131b4967513c1ee90cba4472"),
    ("Bangla Beauty", "6b60d159f0939a45f7b4c88a9b57499a"),
    ("Aztec Priestess", "6acff19b2d911a8c695ba24371964807"),
    ("Fortune Monkey", "add95fc40f1ef0d56f5716ce45a56946"),
    ("Dabanggg", "5404a45b06826911c3537fdf935c281f"),
    ("Sin City", "830cac2f5da6cc1fb91cfae04b85b1e2"),
    ("King Arthur", "fafab1a17a237d0fc0e50c20d2c2bf4c"),
    ("Charge Buffalo Ascent", "28bc4a33c985ddce6acd92422626b76f"),
    ("Witches Night", "82c5c404cf4c0790deb42a2b5653533c"),
    ("Big Small", "25822eb4d6459cc8b39c4f7b69b1bf2c"),
    ("Number King", "36d20c24669dca7630715f2e0a7c18be"),
    ("Journey West M", "0d0a5a1731a6a05ffeb0e0f9d1948f80"),
    ("Poker King", "a9b13010273fcb0284c9ef436c5fe2ff"),
    ("Dragon & Tiger", "e7ac92d2fdd2aedca92a3521b4416f47"),
    ("iRich Bingo", "a53e46bf1e31f7a960ae314dc188e8b3"),
    ("7up7down", "3aca3084a5c1a8c77c52d6147ee3d2ab"),
    ("Baccarat", "b9c7c5f589cdaa63c4495e69eaa6dbbf"),
    ("Fortune Bingo", "2fd70535a3c838a438b4b8003ecce49d"),
    ("Sic Bo", "de0dc8a7fd369bd39a2d5747be87825c"),
    ("Super Bingo", "c934e67c2a84f52ef4fb598b56f3e7ba"),
    ("Bingo Carnaval", "d419ec9ab6a23590770fd77b036aed16"),
    ("Win Drop", "8211bc6e55e84d266bef9a6960940183"),
    ("Lucky Bingo", "c9f2470e285f3580cd761ba2e1f067e1"),
    ("Jackpot Bingo", "780d43c0a98bc8f6a0705976605608c3"),
    ("Color Game", "2ac4917fbc8b2034307b0c3cdd90d416"),
    ("Go Goal BIngo", "4e5ddaa644badc5f68974a65bf7af02a"),
    ("Calaca Bingo", "b2f05dae5370035a2675025953d1d115"),
    ("PAPPU", "e5091890bbb65a5f9ceb657351fa73c1"),
    ("West Hunter Bingo", "8d2c1506dc4ae4c47d23f9359d71c360"),
    ("Bingo Adventure", "2303867628a9a62272da7576665bbc65"),
    ("Golden Land", "05fc951a633d4c6b4bbe8c429cd63658"),
    ("Candyland Bingo", "711acbdf297ce40a09dd0e9023b63f50"),
    ("Color Prediction", "4a64504353c2304a3061bfd31cd9a62e"),
    ("Magic Lamp Bingo", "848ac1703885d5a86b54fbbf094b3b63"),
    ("Pearls of Bingo", "0995142f4685f66dfdd1a54fffa66ffa"),
    ("European Roulette", "d4fc911a31b3a61edd83bdd95e36f3bf"),
    ("Go Rush", "edef29b5eda8e2eaf721d7315491c51d"),
    ("Mines", "72ce7e04ce95ee94eef172c0dfd6dc17"),
    ("Tower", "8e939551b9e785001fcb5b0a32f88aba"),
    ("HILO", "bd8a2bb2dd63503b93cf6ac9492786ce"),
    ("Limbo", "eabf08253165b6bb2646e403de625d1a"),
    ("Wheel", "6e19e03c50f035ddd9ffd804c30f8c80"),
    ("Mines Gold", "4bceeb28b1a88c87d1ef518d7af2bba9"),
    ("Keno", "a54e3f5e231085c7d8ba99e8ed2261fc"),
    ("Plinko", "e3b71c6844eb8c30f5ef210ad92725a6"),
    ("Crash Bonus", "a7f3e5f210523a989a7c6b32f2f1ad42"),
    ("TeenPatti", "f743cb55c2c4b737727ef144413937f4"),
    ("AK47", "488c377662cad37a551bde18e2fbe785"),
    ("Andar Bahar", "6f48b3aa0b64c79a2dc320ea021148b5"),
    ("Rummy", "ae632f32c3a1e6803f9a6fbec16be28e"),
    ("Callbreak", "9092b5a56e001c60850c4c1184c53e07"),
    ("TeenPatti Joker", "1a4eaca67612e65fdcae43f4c8a667a4"),
    ("Callbreak Quick", "aa9a9916d6e48ba50afa3c2246b6dacb"),
    ("TeenPatti 20-20", "1afa7db588d05de7b9abca4664542765"),
    ("Ludo Quick", "bb1f14d788d37b06dc8f6701ed57ed0d"),
    ("Tongits Go", "26fbfab92a3837b7dbf767e783b173af"),
    ("Pusoy Go", "f2879a3f20f305eadad13448e11c052e"),
    ("Blackjack", "3b502aee6c9e1ef0f698332ee1b76634"),
    ("Blackjack Lucky Ladies", "d0d1c20062e28493e1750f27a1730c48"),
    ("MINI FLUSH", "07afefc388ab6af8cf26f85286f83fae"),
    ("Pool Rummy", "43e7df819bf57722a8917bb328640b30"),
    ("Caribbean Stud Poker", "04c9784b0b1b162b2c86f9ce353da8b7"),
    ("Fortune Gems 3", "63927e939636f45e9d6d0b3717b3b1c1"),
    ("Super Ace Deluxe", "80aad2a10ae6a95068b50160d6c78897"),
    ("3 Coin Treasures", "69c1b4586b5060eefcb45bb479f03437"),
    ("3 Lucky Piggy", "e09d4c9612ea540bc0afabf76e4f9148"),
    ("Poseidon", "50a1bcbc2ef4a5f761e0e4d338a41699"),
    ("3 Pot Dragons", "921dce2d616e5d0577135bb2d9214946"),
    ("Money Pot", "a5acbbb7ae534d303f67cb447dc8723d"),
    ("Nightfall Hunting", "ced5e3de03293fc6fb111298a504cfeb"),
    ("Shōgun", "68724804a3cd30c749e460256b462f00"),
    ("Ultimate Texas Hold'em", "82fa04ccbbf20291128408c014092bce"),
    ("Devil Fire 2", "0426ba674c9dd29de6fa023afcf0640d"),
    ("Legacy of Egypt", "1310248a5eab24b4bf113a6e0ee7962a"),
    ("Lucky Jaguar", "731e642b1fee94725e7313f3dfba8f45"),
    ("Jackpot Joker", "7ed860eef313538545ff7aa2b9290cf9"),
    ("Fortune King Jackpot", "f2b04833d555ef9989748f9ecabd5249"),
    ("Arena Fighter", "71468f38b1fa17379231d50635990c31"),
    ("Trial of Phoenix", "d11ea63b63ec615ae6df589f0b0d53e1"),
    ("Zeus", "4e7c9f4fbe9b5137f21ebd485a9cfa5c"),
    ("Potion Wizard", "fba154365cdf8fad07565cf93bae3521"),
    ("Crazy Hunter 2", "68880d1fcbd274f6b2bf7168276af51d"),
    ("The Pig House", "824736d3e6abff8a0b7e79d784c7b113"),
    ("Money Coming Expand Bets", "3a557646c3abb12201c0b8810a8c0966"),
    ("Party Star", "bfde2986a4eb3a5a559ac8a8c64df461"),
    ("Egypts Glow", "ddac017cb273a590b7aa0e1ad6a52bef"),
    ("Lucky Doggy", "4bf1d6a75d91c725f89aa5985544a087"),
    ("Golden Bank 2", "3a72a27c8851be5a396f51a19654c7c3"),
    ("Fruity Wheel", "921cf987632d65b5e41ab5dffe16d95a"),
    ("Safari Mystery", "56dad0ca19e96dc6ee1038d374712767"),
    ("Treasure Quest", "6bb74b0a57a66850b79ab5c93864cac3"),
    ("Coin Tree", "ca72a7ad1ca4fa2cdc9a1c49c8bb3332"),
    ("3 Coin Wild Horse", "25bff08b69ccd31c238a627b53afff36"),
    ("Jogo do Bicho", "29149ed003ec05873fc164fc139b5606"),
    ("Speed Baccarat", "9e969a7e77e8f61dbe94575e6c96272f"),
    ("Fish Prawn Crab", "a231addcfef742c0c55049a0cde6e674"),
    ("Super Ace Scratch", "0ec0aeb7aad8903bb6ee6b9b9460926a"),
    ("Jhandi Munda", "3a2f7e03e9e86c925ab8c8612f2ea259"),
    ("Boxing Extravaganza", "2469a7a4bdf296f841f59d0a42bba1a8"),
    ("Thai Hilo", "db89731adb091f081381d77eb5a06162"),
    ("Super E-Sabong", "706342709fa0e5f40068e4e6d81f7358"),
    ("Cricket Roulette", "b761552c4191ee73c2c323e34883b57a"),
    ("Fortune Roulette", "858afeefec569d30eb8a041b335e7507"),
    ("Go For Champion", "45a2a090dd3f8c5e51a20e5f7c24830b"),
    ("Fortune Gems Scratch", "d528913b832aba97654b6393b3a915b4"),
    ("Crash Goal", "a8a5f7f458c8507c311ed7e396fdddd8"),
    ("Crash Cricket", "2b3e6d31620ceabbe44d3edb6fd10af3"),
    ("Keno Bonus Number", "7a24f38a556e6c0682d9ad4f22f60452"),
    ("Video Poker", "28d459e6b8bba9a375e65e1f25e8d316"),
    ("Super Ace Joker", "29c66f73e3916b8eb18c2bf78886927d"),
    ("Pirate Queen 2", "4702eb871271aa62ef3f3d78f5d968c1"),
    ("Coin Infinity Surge Reel", "a1ea10a6b30f260b6d6ff17028d38913"),
    ("Sweet Magic", "ae88afcb58415b7802e2c02c40816f17"),
    ("3 Charge Buffalo", "3ea8ed5f8ba2239e6cd49366afb743f8"),
    ("3 Rich pigies", "472f684f667e272e0ccc7ac1529170ca"),
    ("Roma X Deluxe", "b4fe8cea772a7643551a12de806472e8"),
    ("3 LUCKY LION", "7af6be9d29bb593fa0f6516b14b02103"),
    ("Bikini Lady", "702565a827764d10e470a0f76398a978"),
    ("Fortune Coins", "d6d14943efe13dd3bcf1428d0f702024"),
    ("Cricket War", "a4224fdff8b66bd55ab891e2fd879ac1"),
    ("Keno Super Chance", "8f0ea9429cab15f2a48d9f4972d30b52"),
    ("Crash Touchdown", "014c49675e1c22c76352b8047ae6d8eb"),
    ("Keno Extra Bet", "191d02a6e852cd18ce1dd4d175e96cd6"),
    ("3 Coin Treasures 2", "7b4308e95fa25021bae874f9e128c8c3"),
    ("Penalty Kick", "446de3502193f08cdf0c17bf0791eb41"),
]


class Command(BaseCommand):
    help = "Seed JILI provider with games (name, game_uid), image_url from jiliwebp base, category inferred from name."

    def handle(self, *args, **options):
        provider, _ = GameProvider.objects.get_or_create(
            code="jili",
            defaults={"name": "JILI", "is_active": True},
        )
        created = 0
        skipped = 0
        zero = Decimal("0")
        for name, game_uid in JILI_GAMES:
            name = (name or "").strip()[:255]
            game_uid = (game_uid or "").strip()
            if not game_uid:
                continue
            cat_name = infer_category(name)[:255]
            category, _ = GameCategory.objects.get_or_create(
                name=cat_name,
                defaults={"is_active": True},
            )
            image_url = f"{JILI_IMAGE_BASE.rstrip('/')}/{game_uid}.webp"
            _, was_created = Game.objects.get_or_create(
                provider=provider,
                game_uid=game_uid,
                defaults={
                    "name": name,
                    "category": category,
                    "image_url": image_url,
                    "is_active": True,
                    "min_bet": zero,
                    "max_bet": zero,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1
        self.stdout.write(
            self.style.SUCCESS(f"JILI games: {created} created, {skipped} already existed (skipped).")
        )
