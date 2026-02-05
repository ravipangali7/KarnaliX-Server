# Seed referral_tiers SiteContent for dynamic affiliate tiers.

from django.db import migrations


def seed_referral_tiers(apps, schema_editor):
    SiteContent = apps.get_model('core', 'SiteContent')
    default_tiers = [
        {"level": 1, "referrals": 5, "bonus": "₹500", "perReferral": "₹100"},
        {"level": 2, "referrals": 15, "bonus": "₹2,000", "perReferral": "₹150"},
        {"level": 3, "referrals": 30, "bonus": "₹5,000", "perReferral": "₹200"},
        {"level": 4, "referrals": 50, "bonus": "₹10,000", "perReferral": "₹250"},
        {"level": 5, "referrals": 100, "bonus": "₹25,000", "perReferral": "₹300"},
    ]
    SiteContent.objects.get_or_create(key='referral_tiers', defaults={"data": default_tiers})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_seed_placeholder_pages'),
    ]

    operations = [
        migrations.RunPython(seed_referral_tiers, noop),
    ]
