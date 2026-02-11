# Generated manually for User PIN field

import random
import string
from django.db import migrations, models


def generate_pin():
    return ''.join(random.choices(string.digits, k=6))


def backfill_pins(apps, schema_editor):
    User = apps.get_model('core', 'User')
    for user in User.objects.filter(pin=''):
        user.pin = generate_pin()
        user.save(update_fields=['pin'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_add_game_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='pin',
            field=models.CharField(blank=True, help_text='6-digit PIN for confirmations; auto-generated on create', max_length=6),
        ),
        migrations.RunPython(backfill_pins, migrations.RunPython.noop),
    ]
