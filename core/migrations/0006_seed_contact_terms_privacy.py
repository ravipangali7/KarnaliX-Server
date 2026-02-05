# Seed contact, terms, privacy for SiteContent

from django.db import migrations


def seed_contact_terms_privacy(apps, schema_editor):
    SiteContent = apps.get_model('core', 'SiteContent')
    default_contact = {
        "phone": "+91 80008 25980",
        "email": "support@karnalix.com",
        "whatsapp_number": "918000825980",
        "payment_methods": ["eSewa", "Khalti", "Bank Transfer", "UPI", "Cards"],
    }
    default_terms = {
        "body": "Terms of Service content will be available here. Please check back later or contact support for specific queries.",
    }
    default_privacy = {
        "body": "Privacy Policy content will be available here. We are committed to protecting your data. Contact us for any privacy-related questions.",
    }
    SiteContent.objects.get_or_create(key='contact', defaults={"data": default_contact})
    SiteContent.objects.get_or_create(key='terms', defaults={"data": default_terms})
    SiteContent.objects.get_or_create(key='privacy', defaults={"data": default_privacy})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_bonusrule_promo_code'),
    ]

    operations = [
        migrations.RunPython(seed_contact_terms_privacy, noop),
    ]
