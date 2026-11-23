import assert from "node:assert/strict";
import { rentalDays, usd } from "../src/lib/format.js";

// Rental times are Zanzibar wall-clock values. Browser timezone and DST must
// not change the duration returned by the backend's 24-hour rule.
process.env.TZ = "Europe/Berlin";
assert.equal(rentalDays("2026-10-24", "10:00", "2026-10-25", "10:00"), 1);
assert.equal(rentalDays("2026-03-28", "10:00", "2026-03-29", "10:00"), 1);
assert.equal(rentalDays("2026-12-01", "10:00", "2026-12-04", "10:00"), 3);
assert.equal(rentalDays("2026-12-01", "10:00", "2026-12-01", "11:00"), 1);
assert.equal(rentalDays("2026-12-01", "10:00", "2026-12-01", "09:00"), 0);
assert.equal(rentalDays("not-a-date", "10:00", "2026-12-01", "11:00"), 0);
assert.equal(usd(20), String.fromCharCode(36) + "20.00");
assert.equal(usd(20.5), String.fromCharCode(36) + "20.50");
assert.equal(usd("not-a-price"), "—");
console.log("Booking calculation checks passed.");
