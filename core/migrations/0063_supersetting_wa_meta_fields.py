# Replace legacy Meta/Flexgrew SuperSetting fields with wa_* Meta-only fields.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0062_alter_supersetting_flexgrew_otp_template_id"),
    ]

    operations = [
        migrations.RemoveField(model_name="supersetting", name="whatsapp_secret_key"),
        migrations.RemoveField(model_name="supersetting", name="whatsapp_phone_number_id"),
        migrations.RemoveField(model_name="supersetting", name="whatsapp_api_version"),
        migrations.RemoveField(model_name="supersetting", name="whatsapp_otp_template_name"),
        migrations.RemoveField(model_name="supersetting", name="whatsapp_otp_template_language"),
        migrations.RemoveField(model_name="supersetting", name="whatsapp_otp_template_body_param"),
        migrations.RemoveField(model_name="supersetting", name="whatsapp_verify_token"),
        migrations.RemoveField(model_name="supersetting", name="flexgrew_api_key"),
        migrations.RemoveField(model_name="supersetting", name="flexgrew_base_url"),
        migrations.RemoveField(model_name="supersetting", name="flexgrew_otp_template_id"),
        migrations.AddField(
            model_name="supersetting",
            name="wa_access_token",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="supersetting",
            name="wa_phone_number_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="supersetting",
            name="wa_api_version",
            field=models.CharField(blank=True, default="v22.0", max_length=32),
        ),
        migrations.AddField(
            model_name="supersetting",
            name="wa_template_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="supersetting",
            name="wa_template_language",
            field=models.CharField(blank=True, default="en_US", max_length=32),
        ),
        migrations.AddField(
            model_name="supersetting",
            name="wa_webhook_verify_token",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
