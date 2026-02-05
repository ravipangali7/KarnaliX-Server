# Add optional promo_code to BonusRule for apply-promo flow

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_seed_faq_sitecontent'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonusrule',
            name='promo_code',
            field=models.CharField(blank=True, help_text='Optional code for users to apply this rule', max_length=50, null=True, unique=True),
        ),
    ]
