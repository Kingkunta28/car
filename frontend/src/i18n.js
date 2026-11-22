import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en/translation.json";
import it from "./locales/it/translation.json";
import es from "./locales/es/translation.json";
import fr from "./locales/fr/translation.json";
import de from "./locales/de/translation.json";
import pt from "./locales/pt/translation.json";

export const LANGUAGES = [
  { code: "en", label: "English", flag: "\u{1F1EC}\u{1F1E7}" },
  { code: "it", label: "Italiano", flag: "\u{1F1EE}\u{1F1F9}" },
  { code: "es", label: "Espa\u00f1ol", flag: "\u{1F1EA}\u{1F1F8}" },
  { code: "fr", label: "Fran\u00e7ais", flag: "\u{1F1EB}\u{1F1F7}" },
  { code: "de", label: "Deutsch", flag: "\u{1F1E9}\u{1F1EA}" },
  { code: "pt", label: "Portugu\u00eas", flag: "\u{1F1F5}\u{1F1F9}" },
];

const supportedLanguages = LANGUAGES.map(({ code }) => code);
const translations = { en, it, es, fr, de, pt };
// Each locale JSON is the contents of the default namespace, so i18next
// resources must be nested under `translation`.
const resources = Object.fromEntries(
  Object.entries(translations).map(([language, translation]) => [language, { translation }]),
);
let saved = null;
try { saved = localStorage.getItem("rafiki-language"); } catch { /* storage can be disabled by the browser */ }
const queryLanguage = new URLSearchParams(window.location.search).get("lang");
const browserLanguage = navigator.language?.slice(0, 2).toLowerCase();
const initialLanguage = supportedLanguages.includes(saved)
  ? saved
  : supportedLanguages.includes(queryLanguage)
    ? queryLanguage
    : supportedLanguages.includes(browserLanguage)
      ? browserLanguage
      : "en";

i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: "en",
  supportedLngs: supportedLanguages,
  defaultNS: "translation",
  interpolation: { escapeValue: false },
  returnNull: false,
  returnEmptyString: false,
  saveMissing: import.meta.env.DEV,
  missingKeyHandler: (languages, namespace, key) => {
    if (import.meta.env.DEV) {
      console.warn(`[i18n] Missing translation "${namespace}:${key}" for ${languages.join(", ")}`);
    }
  },
  // English is the authoritative final fallback. If a key is missing in both
  // the active language and English, never expose an implementation key.
  parseMissingKeyHandler: () => import.meta.env.DEV ? "[missing translation]" : "Text unavailable",
});

i18n.on("languageChanged", (language) => {
  try { localStorage.setItem("rafiki-language", language); } catch { /* language remains active for this visit */ }
  document.documentElement.lang = language;
});
document.documentElement.lang = initialLanguage;

export default i18n;
