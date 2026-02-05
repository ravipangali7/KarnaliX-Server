# Seed default FAQ for SiteContent (key 'faq')

from django.db import migrations


def seed_faq(apps, schema_editor):
    SiteContent = apps.get_model('core', 'SiteContent')
    default_faq = [
        {"q": "How do I deposit funds?", "a": "You can deposit using eSewa, Khalti, Bank Transfer, or UPI from the Deposit page."},
        {"q": "How long do withdrawals take?", "a": "Withdrawals are processed within 24-48 hours after verification."},
        {"q": "How do I verify my account?", "a": "Go to Profile > KYC Verification and upload your government ID and selfie."},
        {"q": "What is the minimum withdrawal?", "a": "The minimum withdrawal amount is ₹500."},
    ]
    SiteContent.objects.get_or_create(key='faq', defaults={"data": default_faq})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_sitecontent_user_settings'),
    ]

    operations = [
        migrations.RunPython(seed_faq, noop),
    ]
