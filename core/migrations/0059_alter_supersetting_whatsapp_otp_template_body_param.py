# Safer default: hello_world-style templates work without body variables.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0058_supersetting_whatsapp_meta'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supersetting',
            name='whatsapp_otp_template_body_param',
            field=models.BooleanField(default=False),
        ),
    ]
