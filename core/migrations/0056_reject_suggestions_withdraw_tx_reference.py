from django.db import migrations, models


def default_reject_suggestions():
    return {"data": []}


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0055_sitesetting_google_auth_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="supersetting",
            name="reject_reason_suggestions",
            field=models.JSONField(blank=True, default=default_reject_suggestions),
        ),
        migrations.AddField(
            model_name="withdraw",
            name="reference_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="transaction",
            name="reference_id",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
