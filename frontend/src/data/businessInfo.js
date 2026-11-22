/**
 * Public business details displayed by the Contact page and elsewhere.
 * Phone, WhatsApp and email are provided by the existing public Site Settings
 * API; only the Contact page's existing Zanzibar fallback is defined here.
 */
export const BUSINESS_LOCATION_FALLBACK = "Zanzibar, Tanzania";

export function getBusinessInfo(site) {
  const businessName = site?.business_name?.trim() || "Rafiki Car Hire";
  const address = site?.business_address?.trim() || BUSINESS_LOCATION_FALLBACK;
  const phone = site?.business_phone?.trim() || "";
  const whatsappNumber = site?.whatsapp_number?.trim() || "";
  const email = site?.business_email?.trim() || "";
  const encodedAddress = encodeURIComponent(address);

  return {
    businessName,
    location: address,
    address,
    phone,
    phoneHref: phone ? `tel:${phone.replace(/[^\d+]/g, "")}` : "",
    whatsappNumber,
    whatsappDisplay: phone || (whatsappNumber ? `+${whatsappNumber}` : ""),
    email,
    googleMapsUrl: `https://maps.google.com/?q=${encodedAddress}`,
    googleMapsEmbedUrl: `https://maps.google.com/maps?q=${encodedAddress}&z=13&output=embed`,
    // The Contact page has no social links configured, so do not invent any.
    socialLinks: {},
  };
}
