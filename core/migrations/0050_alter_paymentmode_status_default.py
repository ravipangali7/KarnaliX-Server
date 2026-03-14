# Payment mode: default status is approved for all (including player)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0049_add_transaction_processed_by"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentmode",
            name="status",
            field=models.CharField(
                choices=[("approved", "Approved"), ("pending", "Pending"), ("rejected", "Rejected")],
                default="approved",
                max_length=20,
            ),
        ),
    ]
