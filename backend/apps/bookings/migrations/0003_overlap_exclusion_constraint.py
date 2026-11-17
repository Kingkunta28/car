"""Database-level double-booking protection (PostgreSQL only).

No two inventory-blocking bookings of the same vehicle may overlap in time
(pickup → return + turnaround). On SQLite (local development only) this is a
no-op and the application-level locked check in create_booking() applies.
"""
from django.db import migrations

CREATE = [
    "CREATE EXTENSION IF NOT EXISTS btree_gist",
    """ALTER TABLE bookings_booking ADD CONSTRAINT booking_no_vehicle_overlap
       EXCLUDE USING gist (vehicle_id WITH =, tstzrange(pickup_at, blocked_until) WITH &&)
       WHERE (blocks_inventory)""",
]
DROP = ["ALTER TABLE bookings_booking DROP CONSTRAINT IF EXISTS booking_no_vehicle_overlap"]


def _run(statements):
    def op(apps, schema_editor):
        if schema_editor.connection.vendor != "postgresql":
            return
        for sql in statements:
            schema_editor.execute(sql)
    return op


class Migration(migrations.Migration):
    dependencies = [("bookings", "0002_seed_services")]
    operations = [migrations.RunPython(_run(CREATE), _run(DROP))]
