from django.db import migrations, models

import apps.core.files


class Migration(migrations.Migration):
    dependencies = [("bookings", "0009_booking_submission_key")]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="voucher_file",
            field=models.FileField(blank=True, max_length=255, storage=apps.core.files.private_storage,
                                   upload_to=apps.core.files.RandomUploadPath("vouchers")),
        ),
        migrations.AddField(
            model_name="booking",
            name="voucher_sha256",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
