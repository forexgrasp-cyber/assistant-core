"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useI18n } from "./LangProvider";
import { useTheme } from "./ThemeProvider";
import { LANGS, Lang } from "@/lib/i18n";
import { clearToken } from "@/lib/auth";

type NavItem = { path: string; label: string };

const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: "Overview",
    items: [
      { path: "product", label: "Product" },
      { path: "dashboard", label: "Dashboard" },
      { path: "ask", label: "Ask" },
      { path: "help", label: "Help & Demo" },
    ],
  },
  {
    title: "Engage",
    items: [
      { path: "campaigns", label: "Campaigns" },
      { path: "flows", label: "Flows" },
      { path: "flow-editor", label: "Flow Builder" },
      { path: "segments", label: "Segments" },
      { path: "customers", label: "Customers" },
      { path: "roster", label: "Client Roster" },
      { path: "events", label: "Events" },
    ],
  },
  {
    title: "Analyze",
    items: [
      { path: "analytics", label: "Analytics" },
      { path: "retention", label: "Retention" },
      { path: "performance", label: "Performance" },
      { path: "growth", label: "Growth & AI" },
      { path: "experiments", label: "Experiments" },
      { path: "reports", label: "Reports" },
    ],
  },
  {
    title: "Operate",
    items: [
      { path: "ops", label: "Success Ops" },
      { path: "alerts", label: "Alerts" },
      { path: "integrations", label: "Integrations" },
      { path: "presets", label: "Presets" },
      { path: "status", label: "Status" },
    ],
  },
  {
    title: "Account",
    items: [{ path: "settings", label: "Settings" }],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { lang, setLang, t } = useI18n();
  const { theme, toggle } = useTheme();

  const signOut = () => {
    clearToken();
    router.replace("/login");
  };

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0">
      <div className="h-16 flex items-center px-5 border-b border-slate-800">
        <Link href="/" className="flex items-center gap-2 font-bold text-white">
          <span className="bg-indigo-500 text-white px-2 py-0.5 rounded text-xs">RA</span>
          <span className="text-sm">{t("appName")}</span>
        </Link>
        <a
          href="https://snapford.com"
          target="_blank"
          rel="noreferrer noopener"
          className="ml-auto text-xs text-slate-400 hover:text-white"
          title="All Snapford products"
        >
          Snapford ↗
        </a>
      </div>

      <div className="px-3 pt-3">
        <button
          onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))}
          className="w-full flex items-center justify-between px-3 py-2 rounded bg-slate-800 text-xs text-slate-400 hover:bg-slate-700 transition"
        >
          <span>{t("search_placeholder")}</span>
          <kbd className="text-[10px] bg-slate-700 px-1.5 py-0.5 rounded">⌘K</kbd>
        </button>
      </div>

      <nav className="flex-1 px-3 py-3 space-y-4 overflow-y-auto">
        {NAV_GROUPS.map((group) => (
          <div key={group.title}>
            <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              {group.title}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const href = `/${item.path}`;
                const active = pathname === href;
                return (
                  <Link
                    key={item.path}
                    href={href}
                    className={`block px-3 py-1.5 rounded text-sm font-medium transition ${
                      active
                        ? "bg-indigo-600 text-white"
                        : "hover:bg-slate-800 hover:text-white"
                    }`}
                  >
                    {t(`nav_${item.path.replace(/-/g, "_")}`) !== `nav_${item.path.replace(/-/g, "_")}`
                      ? t(`nav_${item.path.replace(/-/g, "_")}`)
                      : item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="px-3 py-3 border-t border-slate-800 space-y-2">
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-500">{t("lang")}:</span>
          {LANGS.map((l) => (
            <button
              key={l.id}
              onClick={() => setLang(l.id as Lang)}
              className={`text-xs px-2 py-1 rounded ${
                lang === l.id ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-800"
              }`}
            >
              {l.id.toUpperCase()}
            </button>
          ))}
        </div>
        <button
          onClick={toggle}
          className="w-full flex items-center justify-between px-3 py-2 rounded bg-slate-800 text-xs text-slate-300 hover:bg-slate-700 transition"
          title="Press T"
        >
          <span>{theme === "dark" ? t("theme_dark") : t("theme_light")}</span>
          <span className="text-base">{theme === "dark" ? "🌙" : "☀️"}</span>
        </button>
        <button
          onClick={signOut}
          className="w-full rounded bg-slate-800 px-3 py-2 text-left text-xs text-slate-300 hover:bg-slate-700 transition"
        >
          Sign out
        </button>
        <div className="text-xs text-slate-500 px-1">{t("portal")}</div>
      </div>
    </aside>
  );
}
