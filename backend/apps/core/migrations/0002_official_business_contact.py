from django.db import migrations, models


LOCATION = "Abeid Amani Karume International Airport, Zanzibar, Tanzania"
PHONE = "+255 715 518 980"
WHATSAPP = "255715518980"


def update_site_settings(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.all().update(
        business_address=LOCATION,
        business_phone=PHONE,
        whatsapp_number=WHATSAPP,
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="business_phone",
            field=models.CharField(blank=True, default=PHONE, max_length=40),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="whatsapp_number",
            field=models.CharField(
                blank=True,
                default=WHATSAPP,
                help_text="Official international WhatsApp number in digits only.",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="business_address",
            field=models.CharField(default=LOCATION, max_length=255),
        ),
        migrations.RunPython(update_site_settings, migrations.RunPython.noop),
    ]
