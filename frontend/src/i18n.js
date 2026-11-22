import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en/translation.json";
import it from "./locales/it/translation.json";
import es from "./locales/es/translation.json";
import fr from "./locales/fr/translation.json";
import de from "./locales/de/translation.json";
import pt from "./locales/pt/translation.json";

export const LANGUAGES = [
  { code: "en", label: "English", flag: "🇬🇧" },
  { code: "it", label: "Italiano", flag: "🇮🇹" },
  { code: "es", label: "Español", flag: "🇪🇸" },
  { code: "fr", label: "Français", flag: "🇫🇷" },
  { code: "de", label: "Deutsch", flag: "🇩🇪" },
  { code: "pt", label: "Português", flag: "🇵🇹" },
];

const resources = { en, it, es, fr, de, pt };
let saved = null;
try { saved = localStorage.getItem("rafiki-language"); } catch { /* storage can be disabled by the browser */ }
const queryLanguage = new URLSearchParams(window.location.search).get("lang");
const browserLanguage = navigator.language?.slice(0, 2).toLowerCase();
const initialLanguage = saved || (resources[queryLanguage] ? queryLanguage : resources[browserLanguage] ? browserLanguage : "en");

i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: "en",
  supportedLngs: LANGUAGES.map(({ code }) => code),
  defaultNS: "translation",
  interpolation: { escapeValue: false },
  returnNull: false,
});

i18n.on("languageChanged", (language) => {
  try { localStorage.setItem("rafiki-language", language); } catch { /* language remains active for this visit */ }
  document.documentElement.lang = language;
});
document.documentElement.lang = initialLanguage;

export default i18n;
