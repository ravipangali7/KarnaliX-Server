# WhatsApp webhook verify token + WABA message tracking on OTP rows

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0059_alter_supersetting_whatsapp_otp_template_body_param'),
    ]

    operations = [
        migrations.AddField(
            model_name='supersetting',
            name='whatsapp_verify_token',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='passwordresetotp',
            name='waba_message_id',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='passwordresetotp',
            name='whatsapp_delivery_status',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='signupotp',
            name='waba_message_id',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='signupotp',
            name='whatsapp_delivery_status',
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
