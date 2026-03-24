# Generated manually for Meta WhatsApp Cloud API fields on SuperSetting

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0057_alter_supersetting_reject_reason_suggestions'),
    ]

    operations = [
        migrations.AddField(
            model_name='supersetting',
            name='whatsapp_api_version',
            field=models.CharField(blank=True, default='v22.0', max_length=32),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='whatsapp_otp_template_body_param',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='whatsapp_otp_template_language',
            field=models.CharField(blank=True, default='en_US', max_length=32),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='whatsapp_otp_template_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='whatsapp_phone_number_id',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='whatsapp_secret_key',
            field=models.TextField(blank=True),
        ),
    ]
