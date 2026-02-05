# Generated manually for KYC rejection remarks

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='kycverification',
            name='rejection_remarks',
            field=models.TextField(blank=True, null=True),
        ),
    ]
