/** Verified public details used across the website and kept language-neutral. */
export const businessInfo = Object.freeze({
  location: "Abeid Amani Karume International Airport, Zanzibar, Tanzania",
  phone: "+255 715 518 980",
  whatsapp: "255715518980",
});

export function getBusinessInfo(site) {
  const businessName = site?.business_name?.trim() || "Rafiki Car Hire";
  const address = businessInfo.location;
  const phone = businessInfo.phone;
  const whatsappNumber = businessInfo.whatsapp;
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
