# Add CTA label and link to Promotion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0050_alter_paymentmode_status_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="promotion",
            name="cta_label",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="promotion",
            name="cta_link",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
