// i18n: English + German dictionaries for nav, layout, and common UI strings.
// Add languages by extending LANGS and DICTS; the switcher persists in localStorage.

export type Lang = "en" | "de";

export const LANGS: { id: Lang; label: string }[] = [
  { id: "en", label: "English" },
  { id: "de", label: "Deutsch" },
];

export const DICTS: Record<Lang, Record<string, string>> = {
  en: {
    appName: "Retention Analytics",
    portal: "Customer Portal",
    nav_product: "Product",
    nav_status: "Status",
    nav_dashboard: "Dashboard",
    nav_campaigns: "Campaigns",
    nav_flows: "Flows",
    nav_customers: "Customers",
    nav_segments: "Segments",
    nav_analytics: "Analytics",
    nav_growth: "Growth & AI",
    nav_experiments: "Experiments",
    nav_ops: "Success Ops",
    nav_integrations: "Integrations",
    nav_events: "Events",
    nav_reports: "Reports",
    nav_presets: "Presets",
    nav_help: "Help & Demo",
    nav_settings: "Settings",
    nav_flow_editor: "Flow Builder",
    nav_alerts: "Alerts",
    nav_roster: "Client Roster",
    nav_performance: "Performance",
    nav_ask: "Ask",
    nav_retention: "Retention",
    search_placeholder: "Search or jump to… (Ctrl+K)",
    theme_dark: "Dark",
    theme_light: "Light",
    lang: "Language",
    copy: "Copy",
    copied: "Copied!",
    loading: "Loading…",
    empty: "Nothing here yet",
    run: "Run",
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    create: "Create",
    close: "Close",
    back: "Back",
    next: "Next",
    results: "Results",
    status: "Status",
    name: "Name",
    actions: "Actions",
  },
  de: {
    appName: "Retention Analytics",
    portal: "Kundenportal",
    nav_product: "Produkt",
    nav_status: "Status",
    nav_dashboard: "Übersicht",
    nav_campaigns: "Kampagnen",
    nav_flows: "Flows",
    nav_customers: "Kunden",
    nav_segments: "Segmente",
    nav_analytics: "Analytik",
    nav_growth: "Wachstum & KI",
    nav_experiments: "Experimente",
    nav_ops: "Success Ops",
    nav_integrations: "Integrationen",
    nav_events: "Ereignisse",
    nav_reports: "Berichte",
    nav_presets: "Vorlagen",
    nav_help: "Hilfe & Demo",
    nav_settings: "Einstellungen",
    nav_flow_editor: "Flow-Builder",
    nav_alerts: "Warnungen",
    nav_roster: "Kundenliste",
    nav_performance: "Performance",
    nav_ask: "Ask",
    nav_retention: "Retention",
    search_placeholder: "Suchen oder springen… (Strg+K)",
    theme_dark: "Dunkel",
    theme_light: "Hell",
    lang: "Sprache",
    copy: "Kopieren",
    copied: "Kopiert!",
    loading: "Lädt…",
    empty: "Hier ist noch nichts",
    run: "Starten",
    save: "Speichern",
    cancel: "Abbrechen",
    delete: "Löschen",
    create: "Erstellen",
    close: "Schließen",
    back: "Zurück",
    next: "Weiter",
    results: "Ergebnisse",
    status: "Status",
    name: "Name",
    actions: "Aktionen",
  },
};

const KEY = "ra_lang";

export function getLang(): Lang {
  if (typeof window === "undefined") return "en";
  const v = window.localStorage.getItem(KEY);
  return v === "de" ? "de" : "en";
}

export function setLang(l: Lang) {
  if (typeof window !== "undefined") window.localStorage.setItem(KEY, l);
}

export function t(lang: Lang, key: string): string {
  return DICTS[lang][key] ?? DICTS.en[key] ?? key;
}
