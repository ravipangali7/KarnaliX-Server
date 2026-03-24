# Generated manually for email-based signup OTP/session

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0057_alter_supersetting_reject_reason_suggestions'),
    ]

    operations = [
        migrations.AddField(
            model_name='signupotp',
            name='email',
            field=models.EmailField(blank=True, db_index=True, default='', max_length=254),
        ),
        migrations.AlterField(
            model_name='signupotp',
            name='phone',
            field=models.CharField(blank=True, db_index=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='signupsession',
            name='email',
            field=models.EmailField(blank=True, db_index=True, default='', max_length=254),
        ),
        migrations.AlterField(
            model_name='signupsession',
            name='phone',
            field=models.CharField(blank=True, db_index=True, default='', max_length=20),
        ),
    ]
