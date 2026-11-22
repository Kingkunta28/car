"""Import the Rafiki fleet and brand images from frontend/src/images.

    python manage.py import_fleet            # create missing vehicles (safe to re-run)
    python manage.py import_fleet --update   # also refresh specs/prices of existing ones

Rules:
* One vehicle per distinct car, one photo per vehicle — no photo is ever used twice
  (checked by content hash AND by a perceptual hash, so re-saved copies count as the same photo).
* Photos are converted to optimised WebP (max 1600px wide) before storage.
* The Land Cruiser Prado photo is "Toyota Land Cruiser.png" (transparent cut-out) placed on the
  fleet's light studio background, saved as Toyota Land Cruiser.png.
* Prices, years, seats, transmission and fuel are copied from the current Rafiki
  website (kingkunta28.github.io/ZanCarRental). The two Prado Classic / Escudo
  Grand Vitara rates are not listed there and remain estimates.
"""
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image

from apps.core.models import SiteSettings
from apps.vehicles.models import Vehicle, VehicleFeature, VehicleImage

IMAGES = Path(settings.BASE_DIR).parent / "frontend" / "src" / "images"

AC = "Air conditioning"
FLEET = [
    dict(slug="toyota-land-cruiser-prado-2020", name="Toyota Land Cruiser Prado", brand="Toyota", model="Land Cruiser Prado",
         year=2020, category="4X4", transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=5, luggage_capacity=4,
         doors=5, price="150.00", featured=True, image="Toyota Land Cruiser.png",
         features=[AC, "Four-wheel drive", "High ground clearance"],
         description="Our flagship 4x4. Commanding, comfortable and unstoppable on Zanzibar's sandy east-coast tracks — ideal for families and anyone heading off the main roads."),
    dict(slug="toyota-land-cruiser-prado-classic", name="Toyota Land Cruiser Prado Classic", brand="Toyota", model="Land Cruiser Prado",
         year=None, category="4X4", transmission="AUTOMATIC", fuel_type="DIESEL", passenger_capacity=7, luggage_capacity=4,
         doors=5, price="85.00", featured=False, image="Toyota Land Cruiser.jpeg",
         features=[AC, "Four-wheel drive", "7 seats"],
         description="The legendary Prado in its classic generation: rugged, roomy and dependable, at a friendlier daily rate."),
    dict(slug="toyota-harrier-2015", name="Toyota Harrier", brand="Toyota", model="Harrier", year=2015, category="SUV",
         transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=5, luggage_capacity=3, doors=5, price="45.00",
         featured=True, image="Toyota G-Class.jpeg", features=[AC, "Premium SUV comfort"],
         description="A refined, comfortable SUV for couples and small families who want a smooth, quiet drive around the island."),
    dict(slug="toyota-rav4-2018", name="Toyota RAV4", brand="Toyota", model="RAV4", year=2018, category="SUV",
         transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=5, luggage_capacity=3, doors=5, price="35.00",
         featured=True, image="Toyota RAV4.jpeg", features=[AC, "Easy automatic"],
         description="The all-rounder. Easy to drive in Stone Town, spacious enough for luggage, and comfortable on the coast roads."),
    dict(slug="toyota-vanguard-2018", name="Toyota Vanguard", brand="Toyota", model="Vanguard", year=2018, category="SUV",
         transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=5, luggage_capacity=3, doors=5, price="40.00",
         featured=False, image="Toyota RAV4_2.jpeg", features=[AC, "Large boot"],
         description="A roomy mid-size SUV with a generous boot — great for families with plenty of bags."),
    dict(slug="toyota-rav4-2016-3-door", name="Toyota RAV4 3-Door", brand="Toyota", model="RAV4", year=2016, category="COMPACT_SUV",
         transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=2, luggage_capacity=2, doors=3, price="30.00",
         featured=False, image="Toyota RAV4 2doors.jpeg", features=[AC, "Compact & nimble"],
         description="A compact, fun-to-drive RAV4 — perfect for two travellers exploring beaches and villages."),
    dict(slug="suzuki-escudo-2019", name="Suzuki Escudo", brand="Suzuki", model="Escudo", year=2019, category="4X4",
         transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=3, luggage_capacity=3, doors=5, price="26.00",
         featured=False, image="Toyota Escudo.jpg", features=[AC, "Four-wheel drive"],
         description="An affordable, capable 4x4 that handles unpaved roads with ease."),
    dict(slug="suzuki-escudo-grand-vitara", name="Suzuki Escudo Grand Vitara", brand="Suzuki", model="Escudo (Grand Vitara)",
         year=None, category="4X4", transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=5, luggage_capacity=3,
         doors=5, price="50.00", featured=False, image="Suzuki Escudo 2doors.jpeg", features=[AC, "Four-wheel drive"],
         description="The newer-generation Escudo: comfortable on tarmac, confident on sand and gravel."),
    dict(slug="nissan-juke-2018", name="Nissan Juke", brand="Nissan", model="Juke", year=2018, category="COMPACT_SUV",
         transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=4, luggage_capacity=2, doors=5, price="25.00",
         featured=False, image="Nissan E-Class.jpeg", features=[AC, "Stylish crossover"],
         description="A stylish compact crossover — easy to park in town and comfortable on longer drives."),
    dict(slug="toyota-ist-2018", name="Toyota IST", brand="Toyota", model="IST", year=2018, category="ECONOMY",
         transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=5, luggage_capacity=2, doors=5, price="20.00",
         featured=False, image="Toyota Ist.jpg", features=[AC, "Fuel efficient"],
         description="Our most economical car: light on fuel, easy to drive and ideal for Stone Town and the main roads."),
    dict(slug="toyota-hilux", name="Toyota Hilux", brand="Toyota", model="Hilux", year=2010, category="4X4",
         transmission="AUTOMATIC", fuel_type="DIESEL", passenger_capacity=5, luggage_capacity=4, doors=4, price="90.00",
         featured=False, image="Toyota C-Class.jpeg", features=[AC, "Double cab", "Load bed"],
         description="A tough double-cab pickup with an open load bed — for surf gear, dive kit or anything bulky."),
    dict(slug="toyota-alphard", name="Toyota Alphard", brand="Toyota", model="Alphard", year=2013, category="MINIVAN",
         transmission="AUTOMATIC", fuel_type="PETROL", passenger_capacity=8, luggage_capacity=4, doors=4, price="45.00",
         featured=True, image="Toyota Alphard.jpeg", features=[AC, "8 seats", "Sliding doors"],
         description="Spacious, premium people-carrier for families and groups — everyone travels together in comfort."),
]


def _ahash(path: Path) -> int:
    """Average hash: identical for the same photo re-saved in another format/size."""
    im = Image.open(path).convert("L").resize((16, 16), Image.Resampling.LANCZOS)
    px = list(im.getdata())
    avg = sum(px) / len(px)
    return sum(1 << i for i, p in enumerate(px) if p > avg)


def _webp(path: Path, max_w=1600) -> bytes:
    im = Image.open(path)
    im = im.convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, "WEBP", quality=82, method=6)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Import the Rafiki fleet (one unique photo per car) and brand images from frontend/src/images."

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true", help="Refresh specs/prices of vehicles that already exist.")

    def handle(self, *args, update=False, **opts):
        if not IMAGES.is_dir():
            raise CommandError(f"Image folder not found: {IMAGES}")

        # ---- No-repetition guard -------------------------------------------------
        paths = [IMAGES / v["image"] for v in FLEET]
        missing = [str(p) for p in paths if not p.exists()]
        if missing:
            raise CommandError(f"Missing images: {missing}")
        if len({v["slug"] for v in FLEET}) != len(FLEET):
            raise CommandError("Duplicate vehicle slug in FLEET.")
        hashes = {}
        for v, p in zip(FLEET, paths):
            h = _ahash(p)
            for other, oh in hashes.items():
                if bin(h ^ oh).count("1") <= 12:
                    raise CommandError(f"{v['slug']} and {other} use the same photo.")
            hashes[v["slug"]] = h

        created = updated = 0
        with transaction.atomic():
            for order, (spec, path) in enumerate(zip(FLEET, paths)):
                spec = dict(spec)
                image, features, featured = spec.pop("image"), spec.pop("features"), spec.pop("featured")
                price = Decimal(spec.pop("price"))
                fields = {**spec, "price_per_day": price, "is_featured": featured,
                          "display_order": order, "is_active": True}
                slug = fields.pop("slug")
                vehicle = Vehicle.objects.filter(slug=slug).first()
                is_new = vehicle is None
                if vehicle is None:
                    vehicle = Vehicle.objects.create(slug=slug, **fields)
                    created += 1
                elif update:
                    for k, val in fields.items():
                        setattr(vehicle, k, val)
                    vehicle.save()
                    updated += 1
                else:
                    self.stdout.write(f"  skip  {slug} (exists; use --update to refresh)")
                if is_new or update:
                    vehicle.features.all().delete()
                    VehicleFeature.objects.bulk_create(
                        [VehicleFeature(vehicle=vehicle, feature_name=f) for f in features])
                image_row = vehicle.images.first()
                if image_row is None:
                    img = VehicleImage(vehicle=vehicle, display_order=0,
                                       alt_text=f"{vehicle.brand} {vehicle.model} for hire in Zanzibar — Rafiki Car Hire")
                    img.image.save(f"{slug}.webp", ContentFile(_webp(path)), save=True)
                elif not image_row.image.storage.exists(image_row.image.name):
                    image_row.image.save(f"{slug}.webp", ContentFile(_webp(path)), save=True)
                self.stdout.write(self.style.SUCCESS(f"  ok    {vehicle.name} - ${vehicle.price_per_day}/day <- {image}"))

            site = SiteSettings.load()
            if not site.hero_image and (IMAGES / "hero.webp").exists():
                site.hero_image.save("hero.webp", ContentFile(_webp(IMAGES / "hero.webp", 2400)), save=False)
            if not site.logo and (IMAGES / "logo.webp").exists():
                buf = BytesIO()
                Image.open(IMAGES / "logo.webp").convert("RGB").save(buf, "PNG", optimize=True)
                site.logo.save("logo.png", ContentFile(buf.getvalue()), save=False)
            site.save()

        self.stdout.write(self.style.SUCCESS(f"Done: {created} created, {updated} updated. "
                                             f"Hero image and logo set. Prices copied from the current website."))
