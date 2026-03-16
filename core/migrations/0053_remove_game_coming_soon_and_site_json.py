# Remove game coming-soon fields and site_coming_soon_json (replaced by ComingSoon model)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0052_comingsoon"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="game",
            name="is_coming_soon",
        ),
        migrations.RemoveField(
            model_name="game",
            name="coming_soon_launch_date",
        ),
        migrations.RemoveField(
            model_name="game",
            name="coming_soon_description",
        ),
        migrations.RemoveField(
            model_name="sitesetting",
            name="site_coming_soon_json",
        ),
    ]
