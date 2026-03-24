# Flexgrew API credentials + optional OTP template id (SuperSetting)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0060_whatsapp_webhook_verify_and_waba_ids'),
    ]

    operations = [
        migrations.AddField(
            model_name='supersetting',
            name='flexgrew_api_key',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='flexgrew_base_url',
            field=models.CharField(blank=True, max_length=512),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='flexgrew_otp_template_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
