from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("bookings", "0006_vehicle_booking_snapshots")]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="language",
            field=models.CharField(
                choices=[("en", "English"), ("it", "Italian"), ("es", "Spanish"),
                         ("fr", "French"), ("de", "German"), ("pt", "Portuguese")],
                default="en",
                max_length=2,
            ),
        ),
    ]
