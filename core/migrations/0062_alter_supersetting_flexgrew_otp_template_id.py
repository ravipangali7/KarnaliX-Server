# Store Flexgrew template id as string (no PositiveInteger max validation)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0061_supersetting_flexgrew_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supersetting',
            name='flexgrew_otp_template_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
