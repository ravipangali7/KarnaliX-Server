from django.db import migrations, models


def backfill_slider_images(apps, schema_editor):
    SliderSlide = apps.get_model("core", "SliderSlide")
    for slide in SliderSlide.objects.all():
        changed = False
        legacy_file = getattr(slide, "image_file", None)
        if legacy_file:
            if not getattr(slide, "mobile_image", None):
                slide.mobile_image = legacy_file
                changed = True
            if not getattr(slide, "desktop_image", None):
                slide.desktop_image = legacy_file
                changed = True
        if changed:
            slide.save(update_fields=["mobile_image", "desktop_image"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0064_user_whatsapp_deposit_withdraw"),
    ]

    operations = [
        migrations.AddField(
            model_name="sliderslide",
            name="desktop_image",
            field=models.ImageField(blank=True, null=True, upload_to="slider/"),
        ),
        migrations.AddField(
            model_name="sliderslide",
            name="mobile_image",
            field=models.ImageField(blank=True, null=True, upload_to="slider/"),
        ),
        migrations.RunPython(backfill_slider_images, migrations.RunPython.noop),
    ]
