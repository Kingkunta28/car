const photo = (slug, url, alt) => ({ id: `default-${slug}`, url, alt_text: alt, display_order: 0 });

// The frontend owns the public catalogue. These records and local photos keep
// the fleet available even when the booking API or its database is unavailable.
export const DEFAULT_VEHICLES = [
  { slug: "toyota-land-cruiser-prado-2020", name: "Toyota Land Cruiser Prado", brand: "Toyota", model: "Land Cruiser Prado", year: 2020, category: "4X4", category_display: "4x4", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 5, luggage_capacity: 4, doors: 5, price_per_day: "150.00", description: "Our flagship 4x4. Commanding, comfortable and ready for Zanzibar's sandy east-coast tracks.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: true, features: ["Air conditioning", "Four-wheel drive", "High ground clearance"], mainImage: "/images/cars/toyota-land-cruiser-prado-2020.png", galleryImages: [] },
  { slug: "toyota-land-cruiser-prado-classic", name: "Toyota Land Cruiser Prado Classic", brand: "Toyota", model: "Land Cruiser Prado", year: null, category: "4X4", category_display: "4x4", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "DIESEL", fuel_type_display: "Diesel", passenger_capacity: 7, luggage_capacity: 4, doors: 5, price_per_day: "85.00", description: "A roomy classic Prado: rugged, dependable and ready for island journeys.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: false, features: ["Air conditioning", "Four-wheel drive", "7 seats"], mainImage: "/images/cars/toyota-land-cruiser-prado-classic.jpeg", galleryImages: [] },
  { slug: "toyota-harrier-2015", name: "Toyota Harrier", brand: "Toyota", model: "Harrier", year: 2015, category: "SUV", category_display: "SUV", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 5, luggage_capacity: 3, doors: 5, price_per_day: "45.00", description: "A refined, comfortable SUV for couples and small families exploring the island.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: true, features: ["Air conditioning", "Premium SUV comfort"], mainImage: "/images/cars/toyota-harrier-2015.jpeg", galleryImages: [] },
  { slug: "toyota-rav4-2018", name: "Toyota RAV4", brand: "Toyota", model: "RAV4", year: 2018, category: "SUV", category_display: "SUV", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 5, luggage_capacity: 3, doors: 5, price_per_day: "35.00", description: "An easy-to-drive all-rounder with room for luggage and comfort on the coast roads.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: true, features: ["Air conditioning", "Easy automatic"], mainImage: "/images/cars/toyota-rav4-2018.jpeg", galleryImages: [] },
  { slug: "toyota-vanguard-2018", name: "Toyota Vanguard", brand: "Toyota", model: "Vanguard", year: 2018, category: "SUV", category_display: "SUV", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 5, luggage_capacity: 3, doors: 5, price_per_day: "40.00", description: "A roomy mid-size SUV with a generous boot for family luggage.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: false, features: ["Air conditioning", "Large boot"], mainImage: "/images/cars/toyota-vanguard-2018.jpeg", galleryImages: [] },
  { slug: "toyota-rav4-2016-3-door", name: "Toyota RAV4 3-Door", brand: "Toyota", model: "RAV4", year: 2016, category: "COMPACT_SUV", category_display: "Compact SUV", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 2, luggage_capacity: 2, doors: 3, price_per_day: "30.00", description: "A compact RAV4 for two travellers exploring Zanzibar's beaches and villages.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: false, features: ["Air conditioning", "Compact and nimble"], mainImage: "/images/cars/toyota-rav4-2016-3-door.jpeg", galleryImages: [] },
  { slug: "suzuki-escudo-2019", name: "Suzuki Escudo", brand: "Suzuki", model: "Escudo", year: 2019, category: "4X4", category_display: "4x4", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 3, luggage_capacity: 3, doors: 5, price_per_day: "26.00", description: "An affordable, capable 4x4 for paved roads and unpaved island tracks.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: false, features: ["Air conditioning", "Four-wheel drive"], mainImage: "/images/cars/suzuki-escudo-2019.jpg", galleryImages: [] },
  { slug: "suzuki-escudo-grand-vitara", name: "Suzuki Escudo Grand Vitara", brand: "Suzuki", model: "Escudo (Grand Vitara)", year: null, category: "4X4", category_display: "4x4", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 5, luggage_capacity: 3, doors: 5, price_per_day: "50.00", description: "A comfortable Escudo with confidence on tarmac, sand and gravel.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: false, features: ["Air conditioning", "Four-wheel drive"], mainImage: "/images/cars/suzuki-escudo-grand-vitara.jpeg", galleryImages: [] },
  { slug: "nissan-juke-2018", name: "Nissan Juke", brand: "Nissan", model: "Juke", year: 2018, category: "COMPACT_SUV", category_display: "Compact SUV", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 4, luggage_capacity: 2, doors: 5, price_per_day: "25.00", description: "A stylish compact crossover that is easy to park in town and comfortable on longer drives.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: false, features: ["Air conditioning", "Compact crossover"], mainImage: "/images/cars/nissan-juke-2018.jpeg", galleryImages: [] },
  { slug: "toyota-ist-2018", name: "Toyota IST", brand: "Toyota", model: "IST", year: 2018, category: "ECONOMY", category_display: "Economy", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 5, luggage_capacity: 2, doors: 5, price_per_day: "20.00", description: "An economical, easy-to-drive car for Stone Town and the island's main roads.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: false, features: ["Air conditioning", "Fuel efficient"], mainImage: "/images/cars/toyota-ist-2018.jpg", galleryImages: [] },
  { slug: "toyota-hilux", name: "Toyota Hilux", brand: "Toyota", model: "Hilux", year: 2010, category: "4X4", category_display: "4x4", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "DIESEL", fuel_type_display: "Diesel", passenger_capacity: 5, luggage_capacity: 4, doors: 4, price_per_day: "90.00", description: "A tough double-cab pickup for surf gear, dive kit and bulky luggage.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: false, features: ["Air conditioning", "Double cab", "Load bed"], mainImage: "/images/cars/toyota-hilux.jpeg", galleryImages: [] },
  { slug: "toyota-alphard", name: "Toyota Alphard", brand: "Toyota", model: "Alphard", year: 2013, category: "MINIVAN", category_display: "Minivan", transmission: "AUTOMATIC", transmission_display: "Automatic", fuel_type: "PETROL", fuel_type_display: "Petrol", passenger_capacity: 8, luggage_capacity: 4, doors: 4, price_per_day: "45.00", description: "A spacious people-carrier for families and groups travelling together.", availability_status: "AVAILABLE", availability_display: "Available", is_featured: true, features: ["Air conditioning", "8 seats", "Sliding doors"], mainImage: "/images/cars/toyota-alphard.jpeg", galleryImages: [] },
].map((vehicle) => ({
  ...vehicle,
  id: vehicle.slug,
  isDefaultVehicle: true,
  images: [photo(vehicle.slug, vehicle.mainImage, `${vehicle.name} available for hire in Zanzibar`), ...vehicle.galleryImages.map((url, index) => ({ id: `default-${vehicle.slug}-${index + 1}`, url, alt_text: `${vehicle.name} photo ${index + 2}`, display_order: index + 1 }))],
}));

export const DEFAULT_BOOKING_OPTIONS = {
  isFallback: true,
  currency: "USD",
  tax_rate: "0.00",
  tax_label: "VAT",
  locations: [
    { code: "AIRPORT", label: "Zanzibar Airport", fee: "0.00" },
    { code: "TOWN", label: "Zanzibar Town", fee: "0.00" },
    { code: "OUTSIDE_ZONE", label: "Outside Free Zone", fee: "25.00" },
  ],
  extras: [
    { code: "baby_seat", name: "Baby seat", description: "Per seat, for the whole booking (not per day).", price: "60.00", pricing_type: "PER_UNIT", max_quantity: 4, bulk_min_quantity: null, bulk_unit_price: null, requires_documents: false },
    { code: "driving_permit", name: "Driving permit arrangement", description: "We arrange the Zanzibar driving permit. Requires passport and driving licence copies.", price: "25.00", pricing_type: "PER_BOOKING", max_quantity: 1, bulk_min_quantity: null, bulk_unit_price: null, requires_documents: true },
  ],
  default_arrival_airport: "Abeid Amani Karume International Airport",
  hold_hours: 24,
  min_lead_hours: 0,
  max_rental_days: 30,
  max_upload_mb: 8,
  payment_methods: {
    manual: { available: true, instructions: "Payment instructions will be shared after your booking is received." },
    online: { available: false, gateways: [] },
  },
};

export function findDefaultVehicle(slug) {
  return DEFAULT_VEHICLES.find((vehicle) => vehicle.slug === slug);
}

export function vehicleSnapshot(vehicle) {
  if (!vehicle) return null;
  return {
    id: vehicle.id,
    slug: vehicle.slug,
    name: vehicle.name,
    brand: vehicle.brand,
    model: vehicle.model,
    year: vehicle.year,
    category: vehicle.category,
    category_display: vehicle.category_display,
    description: vehicle.description,
    price_per_day: vehicle.price_per_day,
    transmission: vehicle.transmission,
    transmission_display: vehicle.transmission_display,
    fuel_type: vehicle.fuel_type,
    fuel_type_display: vehicle.fuel_type_display,
    passenger_capacity: vehicle.passenger_capacity,
    luggage_capacity: vehicle.luggage_capacity,
    doors: vehicle.doors,
    features: vehicle.features,
    availability_status: vehicle.availability_status,
    availability_display: vehicle.availability_display,
    main_image: vehicle.mainImage,
    gallery_images: vehicle.galleryImages || [],
  };
}

function matchesFilters(vehicle, params) {
  const term = (params.search || "").trim().toLocaleLowerCase();
  if (term) {
    const searchable = [vehicle.name, vehicle.brand, vehicle.model, vehicle.category_display,
      vehicle.description, ...vehicle.features].join(" ").toLocaleLowerCase();
    if (!searchable.includes(term)) return false;
  }
  if (params.category && vehicle.category !== params.category) return false;
  if (params.transmission && vehicle.transmission !== params.transmission) return false;
  if (params.min_price && Number(vehicle.price_per_day) < Number(params.min_price)) return false;
  if (params.max_price && Number(vehicle.price_per_day) > Number(params.max_price)) return false;
  if (params.min_passengers && vehicle.passenger_capacity < Number(params.min_passengers)) return false;
  return true;
}

export function filterVehicles(params = {}) {
  const fleet = DEFAULT_VEHICLES.filter((vehicle) => matchesFilters(vehicle, params));
  const ordering = params.ordering;
  if (ordering === "price_per_day") fleet.sort((a, b) => Number(a.price_per_day) - Number(b.price_per_day));
  else if (ordering === "-price_per_day") fleet.sort((a, b) => Number(b.price_per_day) - Number(a.price_per_day));
  else if (ordering === "-passenger_capacity") fleet.sort((a, b) => b.passenger_capacity - a.passenger_capacity);
  else if (ordering === "name") fleet.sort((a, b) => a.name.localeCompare(b.name));
  else fleet.sort((a, b) => Number(b.is_featured) - Number(a.is_featured));
  return fleet;
}
