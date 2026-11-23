from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("bookings", "0008_booking_price_rules")]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="submission_key",
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
    ]
