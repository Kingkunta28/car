import { rentalDays } from "./format.js";

const toCents = (amount) => {
  if (amount == null || amount === "") return null;
  const value = Number(amount);
  return Number.isFinite(value) && value >= 0 ? Math.round(value * 100) : null;
};
const asMoney = (cents) => (cents / 100).toFixed(2);

/** Calculate the current booking estimate from the selected static vehicle and priced options. */
export function calculateBookingPrice({ vehicle, pickupDate, pickupTime, returnDate, returnTime,
  pickupType, returnType, extras = {}, options }) {
  const days = rentalDays(pickupDate, pickupTime, returnDate, returnTime);
  if (!vehicle || days < 1) return { ready: false, error: null };

  const dailyRate = toCents(vehicle.price_per_day);
  if (dailyRate == null || dailyRate <= 0) return { ready: true, error: "invalid_vehicle_price" };
  const rentalTotal = dailyRate * days;
  const location = options?.locations?.find((item) => item.code === "OUTSIDE_ZONE");
  const deliveryRate = toCents(location?.fee);
  const isOutside = pickupType === "OUTSIDE_ZONE" || returnType === "OUTSIDE_ZONE";
  if (isOutside && deliveryRate == null) return { ready: true, error: "invalid_delivery_price" };
  // The $25 delivery charge applies once per booking if either leg is outside.
  const pickupFee = isOutside && pickupType === "OUTSIDE_ZONE" ? deliveryRate : 0;
  const returnFee = isOutside && pickupType !== "OUTSIDE_ZONE" ? deliveryRate : 0;

  const services = options?.extras || [];
  const lines = [];
  let extrasTotal = 0;
  let babySeatTotal = 0;
  for (const [code, rawQuantity] of Object.entries(extras)) {
    const quantity = Number(rawQuantity);
    if (!Number.isFinite(quantity) || !Number.isInteger(quantity) || quantity < 0) {
      return { ready: true, error: "invalid_extra_quantity" };
    }
    if (quantity === 0) continue;
    const service = services.find((item) => item.code === code);
    if (!service || quantity > Number(service.max_quantity)) return { ready: true, error: "invalid_extra" };
    const price = toCents(service.price);
    if (price == null) return { ready: true, error: "invalid_extra_price" };
    const bulkPrice = code !== "baby_seat" && service.bulk_min_quantity
      && service.bulk_unit_price != null && quantity >= Number(service.bulk_min_quantity)
      ? toCents(service.bulk_unit_price)
      : null;
    const unitPrice = bulkPrice ?? price;
    const multiplier = {
      PER_BOOKING: 1,
      PER_UNIT: quantity,
      PER_DAY: days,
      PER_UNIT_PER_DAY: quantity * days,
    }[service.pricing_type];
    if (multiplier == null) return { ready: true, error: "invalid_extra_pricing" };
    const total = unitPrice * multiplier;
    extrasTotal += total;
    if (code === "baby_seat") babySeatTotal += total;
    lines.push({ code, description: service.name, quantity, unit_price: asMoney(unitPrice), total: asMoney(total), kind: "extra" });
  }

  const subtotal = rentalTotal + pickupFee + returnFee + extrasTotal;
  const taxRate = Number(options?.tax_rate ?? 0);
  if (!Number.isFinite(taxRate) || taxRate < 0) return { ready: true, error: "invalid_tax_rate" };
  const taxAmount = Math.round(subtotal * taxRate / 100);
  return {
    ready: true,
    rental_days: days,
    daily_rate: asMoney(dailyRate),
    rental_total: asMoney(rentalTotal),
    pickup_fee: asMoney(pickupFee),
    return_fee: asMoney(returnFee),
    delivery_fee: asMoney(pickupFee + returnFee),
    extras_total: asMoney(extrasTotal),
    baby_seat_total: asMoney(babySeatTotal),
    lines,
    subtotal: asMoney(subtotal),
    tax_rate: String(taxRate.toFixed(2)),
    tax_label: options?.tax_label || "",
    tax_amount: asMoney(taxAmount),
    grand_total: asMoney(subtotal + taxAmount),
  };
}
