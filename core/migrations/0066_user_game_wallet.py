from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0065_sliderslide_mobile_desktop_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='game_wallet',
            field=models.CharField(
                blank=True,
                default='main',
                help_text='Tracks which wallet (main/bonus) was sent to provider at last game launch. Updated at launch; read at callback.',
                max_length=10,
            ),
        ),
    ]
