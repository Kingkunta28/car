import uuid

from django.db import migrations, models
import django.db.models.deletion

import apps.core.files


class Migration(migrations.Migration):
    dependencies = [("bookings", "0004_extra_bulk_pricing")]

    operations = [
        migrations.CreateModel(
            name="BookingDossier",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("pdf_file", models.FileField(blank=True, max_length=255,
                                              storage=apps.core.files.private_storage,
                                              upload_to=apps.core.files.RandomUploadPath("dossiers"))),
                ("source_digest", models.CharField(blank=True, max_length=64)),
                ("booking", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name="dossier", to="bookings.booking")),
            ],
            options={"abstract": False},
        ),
    ]
