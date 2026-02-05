# Add min_deposit, min_withdraw, referral_amount to contact SiteContent

from django.db import migrations


def add_contact_amounts(apps, schema_editor):
    SiteContent = apps.get_model('core', 'SiteContent')
    try:
        row = SiteContent.objects.get(key='contact')
    except SiteContent.DoesNotExist:
        return
    data = dict(row.data) if row.data else {}
    data.setdefault('min_deposit', 500)
    data.setdefault('min_withdraw', 500)
    data.setdefault('referral_amount', '500')
    row.data = data
    row.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_seed_referral_tiers'),
    ]

    operations = [
        migrations.RunPython(add_contact_amounts, noop),
    ]
