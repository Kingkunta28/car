import assert from "node:assert/strict";
import { rentalDays, usd } from "../src/lib/format.js";
import { calculateBookingPrice } from "../src/lib/bookingPrice.js";
import { DEFAULT_BOOKING_OPTIONS, DEFAULT_VEHICLES } from "../src/data/vehicles.js";
import { unitPrice } from "../src/lib/content.js";

// Zanzibar booking times must not shift with a visitor's timezone or DST.
process.env.TZ = "Europe/Berlin";
assert.equal(rentalDays("2026-10-24", "10:00", "2026-10-25", "10:00"), 1);
assert.equal(rentalDays("2026-03-28", "10:00", "2026-03-29", "10:00"), 1);
assert.equal(rentalDays("2026-12-01", "10:00", "2026-12-04", "10:00"), 3);
assert.equal(rentalDays("2026-12-01", "10:00", "2026-12-01", "11:00"), 1);
assert.equal(rentalDays("2026-12-01", "10:00", "2026-12-01", "09:00"), 0);
assert.equal(rentalDays("not-a-date", "10:00", "2026-12-01", "11:00"), 0);
assert.equal(usd(20), String.fromCharCode(36) + "20.00");
assert.equal(usd(20.5), String.fromCharCode(36) + "20.50");
assert.equal(usd("not-a-price"), String.fromCharCode(0x2014));

const vehicle = DEFAULT_VEHICLES.find((item) => item.slug === "toyota-rav4-2018");
const booking = {
  vehicle,
  pickupDate: "2026-12-01", pickupTime: "10:00",
  returnDate: "2026-12-04", returnTime: "10:00",
  pickupType: "AIRPORT", returnType: "TOWN", extras: {}, options: DEFAULT_BOOKING_OPTIONS,
};
const basePrice = calculateBookingPrice(booking);
assert.equal(basePrice.rental_days, 3);
assert.equal(basePrice.rental_total, "105.00");
assert.equal(basePrice.grand_total, "105.00");

const twoSeats = calculateBookingPrice({ ...booking, extras: { baby_seat: 2 } });
assert.equal(twoSeats.baby_seat_total, "120.00");
assert.equal(twoSeats.grand_total, "225.00");
assert.equal(unitPrice({ code: "baby_seat", price: "60.00", bulk_min_quantity: 2, bulk_unit_price: "50.00" }, 2), 60);

for (const locations of [
  { pickupType: "OUTSIDE_ZONE", returnType: "TOWN" },
  { pickupType: "AIRPORT", returnType: "OUTSIDE_ZONE" },
  { pickupType: "OUTSIDE_ZONE", returnType: "OUTSIDE_ZONE" },
]) {
  assert.equal(calculateBookingPrice({ ...booking, ...locations }).delivery_fee, "25.00");
}

const differentVehicle = calculateBookingPrice({ ...booking, vehicle: DEFAULT_VEHICLES.find((item) => item.slug === "toyota-ist-2018") });
assert.equal(differentVehicle.rental_total, "60.00");

const extrasAndTax = calculateBookingPrice({
  ...booking,
  extras: { baby_seat: 2, driving_permit: 1 },
  options: { ...DEFAULT_BOOKING_OPTIONS, tax_rate: "10.00" },
});
assert.equal(extrasAndTax.extras_total, "145.00");
assert.equal(extrasAndTax.grand_total, "275.00");
console.log("Booking calculation checks passed.");
