import { usd } from "./format";

// Prices are never hard-coded: they are read from the booking-options API.
export function priceOf(options, code) {
  return options?.extras?.find((e) => e.code === code)?.price;
}
export function zoneFee(options) {
  return options?.locations?.find((l) => l.code === "OUTSIDE_ZONE")?.fee;
}
const p = (v, fallback = "a small fee") => (v != null ? usd(v) : fallback);

/** Unit price for an extra at a quantity (applies the volume price, e.g. 2+ baby seats). */
export function unitPrice(extra, qty) {
  if (extra?.bulk_min_quantity && extra.bulk_unit_price != null && qty >= extra.bulk_min_quantity) return Number(extra.bulk_unit_price);
  return Number(extra?.price || 0);
}

/** "$60.00 per seat ($50.00 each for 2 or more)" */
export function babySeatText(options) {
  const e = options?.extras?.find((x) => x.code === "baby_seat");
  if (!e) return "available";
  return e.bulk_min_quantity && e.bulk_unit_price != null
    ? `${usd(e.price)} per seat, or ${usd(e.bulk_unit_price)} each for ${e.bulk_min_quantity} or more`
    : `${usd(e.price)} per seat`;
}

export function faqs(options) {
  return [
    {
      q: "Can you deliver the car to Zanzibar Airport?",
      a: `Yes — and it's free. We meet you in the arrivals hall at Abeid Amani Karume International Airport with a name sign, and when you leave we meet you at the departures drop-off. Add your flight details when you book and we'll plan around your arrival time.`,
    },
    {
      q: "Where else can I collect and return the car?",
      a: `Zanzibar Airport and Zanzibar Town (Stone Town area) are free. Anywhere outside the free zone — such as Nungwi, Kendwa, Matemwe, Pongwe, Paje, Jambiani, Bwejuu, Michamvi or Kizimkazi — costs ${p(zoneFee(options))} each way. Pickup and return are charged separately, so you only pay for the leg that's outside the zone.`,
    },
    {
      q: "Do I need a special permit to drive in Zanzibar?",
      a: `Visitors driving in Zanzibar need a local driving permit in addition to their own licence. We can arrange it for you for ${p(priceOf(options, "driving_permit"))} — just upload a copy of your passport and driving licence securely when you book. We assist with the application, but approval is decided by the issuing authority.`,
    },
    {
      q: "Do you have child seats?",
      a: `Yes. Baby and child seats are ${babySeatText(options)} — charged once for your whole rental, not per day. Choose how many you need in the booking form.`,
    },
    {
      q: "Is fuel included?",
      a: "Prices are per day and fuel is not included. Fuel stations are easy to find around Stone Town — fill up before long drives to the coasts.",
    },
    {
      q: "How do I pay?",
      a: "You can pay online by card through our secure payment partner (when available), or choose manual payment such as bank transfer or mobile money. Manual payments are checked by our team before they are marked as paid, and you'll receive a receipt for every verified payment.",
    },
    {
      q: "Is my booking confirmed straight away?",
      a: `When you submit a booking we reserve the car for you and email your invoice immediately. Our team then confirms the booking — usually within a few hours, and always before the reservation hold expires.`,
    },
    {
      q: "How can I reach you during my trip?",
      a: "Message us on WhatsApp day or night — we offer 24/7 support for directions, fuel, breakdowns or anything else you need.",
    },
    {
      q: "Which side of the road do you drive on?",
      a: "Zanzibar drives on the left, like the UK and Kenya. Most of our vehicles are automatic, which makes adjusting easy.",
    },
  ];
}

export const HOW_IT_WORKS = [
  { title: "Choose your car", text: "Browse the fleet and pick a car that suits your group, luggage and itinerary." },
  { title: "Book in minutes", text: "Tell us your dates, where to meet you, and any extras. See the full price before you submit." },
  { title: "Get your invoice", text: "Your invoice arrives instantly by email. We confirm the booking and send you the details." },
  { title: "Drive Zanzibar", text: "Meet us at the airport, in Stone Town or at your hotel — and enjoy the island at your own pace." },
];

export const DESTINATIONS = [
  { name: "Stone Town", time: "Free zone", text: "Narrow streets, spice markets and sunset at Forodhani Gardens." },
  { name: "Nungwi & Kendwa", time: "≈ 1 hr 15 from town", text: "Calm turquoise water and long beaches on the northern tip." },
  { name: "Paje & Jambiani", time: "≈ 1 hr from town", text: "Kite-surfing lagoons and laid-back villages on the south-east coast." },
  { name: "Jozani Forest", time: "≈ 45 min from town", text: "Home of the rare red colobus monkey and mangrove boardwalks." },
];
