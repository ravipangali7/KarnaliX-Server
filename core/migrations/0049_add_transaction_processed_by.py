# Add processed_by to Transaction for account statement "Processed by" display

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0048_sliderslide_cta_blank"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="processed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="processed_transactions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
