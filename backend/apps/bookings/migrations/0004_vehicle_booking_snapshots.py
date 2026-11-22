"""Store booking vehicle snapshots while preserving existing vehicle rows."""
from django.db import migrations, models
import django.db.models.deletion


def populate_vehicle_snapshots(apps, schema_editor):
    Booking = apps.get_model("bookings", "Booking")
    Vehicle = apps.get_model("vehicles", "Vehicle")
    VehicleImage = apps.get_model("vehicles", "VehicleImage")
    VehicleFeature = apps.get_model("vehicles", "VehicleFeature")
    alias = schema_editor.connection.alias
    choices = {
        field: dict(Vehicle._meta.get_field(field).flatchoices)
        for field in ("category", "transmission", "fuel_type", "availability_status")
    }
    batch = []
    for booking in Booking.objects.using(alias).select_related("vehicle").iterator(chunk_size=500):
        vehicle = booking.vehicle
        if vehicle is None:
            slug = "legacy-" + str(booking.pk)
            snapshot = {"id": slug, "slug": slug, "name": "Vehicle", "brand": "", "model": "",
                        "year": None, "price_per_day": str(booking.daily_rate)}
        else:
            images = list(VehicleImage.objects.using(alias).filter(vehicle_id=vehicle.pk).order_by(
                "display_order", "id"))
            features = list(VehicleFeature.objects.using(alias).filter(vehicle_id=vehicle.pk).order_by(
                "display_order", "id").values_list("feature_name", flat=True))
            snapshot = {
                "id": vehicle.slug, "slug": vehicle.slug, "name": vehicle.name, "brand": vehicle.brand,
                "model": vehicle.model, "year": vehicle.year, "category": vehicle.category,
                "category_display": choices["category"].get(vehicle.category, vehicle.category),
                "description": vehicle.description, "price_per_day": str(booking.daily_rate),
                "transmission": vehicle.transmission,
                "transmission_display": choices["transmission"].get(vehicle.transmission, vehicle.transmission),
                "fuel_type": vehicle.fuel_type,
                "fuel_type_display": choices["fuel_type"].get(vehicle.fuel_type, vehicle.fuel_type),
                "passenger_capacity": vehicle.passenger_capacity, "luggage_capacity": vehicle.luggage_capacity,
                "doors": vehicle.doors, "features": features,
                "availability_status": vehicle.availability_status,
                "availability_display": choices["availability_status"].get(vehicle.availability_status,
                                                                             vehicle.availability_status),
                "main_image": images[0].image.url if images else "",
                "gallery_images": [image.image.url for image in images[1:]],
            }
            slug = vehicle.slug
        booking.vehicle_slug = slug
        booking.vehicle_snapshot = snapshot
        batch.append(booking)
        if len(batch) >= 500:
            Booking.objects.using(alias).bulk_update(batch, ["vehicle_slug", "vehicle_snapshot"])
            batch.clear()
    if batch:
        Booking.objects.using(alias).bulk_update(batch, ["vehicle_slug", "vehicle_snapshot"])


def replace_inventory_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE bookings_booking DROP CONSTRAINT IF EXISTS booking_no_vehicle_overlap")
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    schema_editor.execute(
        "ALTER TABLE bookings_booking ADD CONSTRAINT booking_no_vehicle_overlap "
        "EXCLUDE USING gist (vehicle_slug WITH =, tstzrange(pickup_at, blocked_until) WITH &&) "
        "WHERE (blocks_inventory)"
    )


class Migration(migrations.Migration):
    dependencies = [("bookings", "0003_overlap_exclusion_constraint")]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="vehicle_slug",
            field=models.SlugField(blank=True, max_length=140, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="vehicle_snapshot",
            field=models.JSONField(default=dict),
        ),
        migrations.RunPython(populate_vehicle_snapshots, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="booking",
            name="vehicle",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="bookings", to="vehicles.vehicle"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="vehicle_slug",
            field=models.SlugField(db_index=True, max_length=140),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["vehicle_slug", "blocks_inventory", "pickup_at"],
                               name="booking_slug_busy_idx"),
        ),
        migrations.RunPython(replace_inventory_constraint, migrations.RunPython.noop),
    ]
