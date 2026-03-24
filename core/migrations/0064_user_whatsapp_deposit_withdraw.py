from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0063_supersetting_wa_meta_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="whatsapp_deposit",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="user",
            name="whatsapp_withdraw",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
