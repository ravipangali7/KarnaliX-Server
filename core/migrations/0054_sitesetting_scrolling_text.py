from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0053_remove_game_coming_soon_and_site_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesetting",
            name="scrolling_text",
            field=models.TextField(blank=True),
        ),
    ]
