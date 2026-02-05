# Seed placeholder page content keys for About, Careers, Blog, etc.

from django.db import migrations


def seed_placeholder_pages(apps, schema_editor):
    SiteContent = apps.get_model('core', 'SiteContent')
    defaults = [
        ('about', {'body': 'About Us – content TBD. Please check back later or contact support.'}),
        ('careers', {'body': 'Career opportunities – content TBD. Please check back later or contact support.'}),
        ('blog', {'body': 'Blog – content TBD. Please check back later or contact support.'}),
        ('guides', {'body': 'Game Guides – coming soon. Please check back later or contact support.'}),
        ('responsible_gaming', {'body': 'Responsible gaming policy – content TBD. Please check back later or contact support.'}),
        ('kyc', {'body': 'KYC verification policy – content TBD. Please check back later or contact support.'}),
        ('refunds', {'body': 'Refund policy – content TBD. Please check back later or contact support.'}),
        ('chat', {'body': 'Live Chat – use WhatsApp or Contact Us for instant support.'}),
    ]
    for key, data in defaults:
        SiteContent.objects.get_or_create(key=key, defaults={"data": data})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_seed_contact_terms_privacy'),
    ]

    operations = [
        migrations.RunPython(seed_placeholder_pages, noop),
    ]
