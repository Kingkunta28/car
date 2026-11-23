from django.db import migrations, models


OLD_TERMS = (
    "This invoice confirms that a booking request has been received. It is not a confirmation of "
    "the reservation or a receipt of payment. Your reservation is confirmed only when Rafiki Car "
    "Hire confirms it in writing. A payment receipt is issued separately for each verified payment."
)
NEW_TERMS = (
    "This invoice records the selected vehicle, rental dates, customer details and total. "
    "A payment receipt is issued separately for each verified payment."
)


def update_existing_terms(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.filter(invoice_terms=OLD_TERMS).update(invoice_terms=NEW_TERMS)


class Migration(migrations.Migration):
    dependencies = [("core", "0002_official_business_contact")]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="invoice_terms",
            field=models.TextField(
                blank=True,
                default=NEW_TERMS,
            ),
        ),
        migrations.RunPython(update_existing_terms, migrations.RunPython.noop),
    ]
