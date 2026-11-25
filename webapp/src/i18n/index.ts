import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import es from "./es.json";
i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, es: { translation: es } },
  lng:
    window.localStorage?.getItem("finance-locale") ||
    (window.navigator.language.startsWith("es") ? "es" : "en"),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});
export const money = (amount: number) =>
  new Intl.NumberFormat(i18n.language === "es" ? "es-ES" : "en-IE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(amount);
export const number = (value: number, digits = 1) =>
  new Intl.NumberFormat(i18n.language === "es" ? "es-ES" : "en-IE", {
    maximumFractionDigits: digits,
  }).format(value);
export default i18n;
