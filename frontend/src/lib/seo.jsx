import { LANGUAGES } from "../i18n";
import { getBusinessInfo } from "../data/businessInfo";
// React 19 hoists <title>, <meta> and <link> rendered anywhere into <head>.
const SITE_URL = (import.meta.env.VITE_SITE_URL || "https://car-lovat-two.vercel.app").replace(/\/$/, "");
const DEFAULT_IMAGE = `${SITE_URL}/og-image.jpg`;

export function Seo({ title, description, path = "", image, noindex = false, jsonLd }) {
  const fullTitle = title ? `${title} | Rafiki Car Hire Zanzibar` : "Car Hire Zanzibar | Rafiki Car Hire";
  const url = `${SITE_URL}${path}`;
  return (
    <>
      <title>{fullTitle}</title>
      {description && <meta name="description" content={description} />}
      <link rel="canonical" href={url} />
      {LANGUAGES.map(({ code }) => <link key={code} rel="alternate" hrefLang={code} href={`${url}${url.includes("?") ? "&" : "?"}lang=${code}`} />)}
      {noindex && <meta name="robots" content="noindex, nofollow" />}
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content="Rafiki Car Hire" />
      <meta property="og:title" content={fullTitle} />
      {description && <meta property="og:description" content={description} />}
      <meta property="og:url" content={url} />
      <meta property="og:image" content={image || DEFAULT_IMAGE} />
      <meta name="twitter:card" content="summary_large_image" />
      {jsonLd && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />}
    </>
  );
}

export function businessJsonLd(site) {
  const business = getBusinessInfo(site);
  return {
    "@context": "https://schema.org",
    "@type": "AutoRental",
    name: business.businessName,
    slogan: "Drive Zanzibar with Confidence.",
    url: SITE_URL,
    ...(business.phone && { telephone: business.phone }),
    ...(business.email && { email: business.email }),
    address: { "@type": "PostalAddress", addressLocality: "Zanzibar", addressCountry: "TZ",
      streetAddress: business.address },
    areaServed: { "@type": "Place", name: "Zanzibar (Unguja), Tanzania" },
    priceRange: "$$",
    currenciesAccepted: "USD",
  };
}

export { SITE_URL };
