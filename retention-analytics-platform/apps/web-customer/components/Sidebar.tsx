"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "./LangProvider";
import { useTheme } from "./ThemeProvider";
import { LANGS, Lang } from "@/lib/i18n";

const NAV = [
  "dashboard", "campaigns", "flows", "flow-editor", "customers", "segments", "analytics",
  "growth", "experiments", "ops", "alerts", "integrations", "events", "reports",
  "presets", "help", "settings",
] as const;

export default function Sidebar() {
  const pathname = usePathname();
  const { lang, setLang, t } = useI18n();
  const { theme, toggle } = useTheme();

  return (
    <aside className="w-56 bg-slate-900 text-slate-300 flex flex-col shrink-0">
      <div className="h-16 flex items-center px-5 border-b border-slate-800">
        <Link href="/" className="flex items-center gap-2 font-bold text-white">
          <span className="bg-indigo-500 text-white px-2 py-0.5 rounded text-xs">RA</span>
          <span className="text-sm">{t("appName")}</span>
        </Link>
      </div>

      {/* Search trigger */}
      <div className="px-3 pt-3">
        <button
          onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))}
          className="w-full flex items-center justify-between px-3 py-2 rounded bg-slate-800 text-xs text-slate-400 hover:bg-slate-700 transition"
        >
          <span>{t("search_placeholder")}</span>
          <kbd className="text-[10px] bg-slate-700 px-1.5 py-0.5 rounded">⌘K</kbd>
        </button>
      </div>

      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {NAV.map((p) => {
          const href = `/${p}`;
          const active = pathname === href;
          return (
            <Link
              key={p}
              href={href}
              className={`block px-3 py-2 rounded text-sm font-medium transition ${
                active ? "bg-indigo-600 text-white" : "hover:bg-slate-800 hover:text-white"
              }`}
            >
              {t(`nav_${p === "help" ? "help" : p === "flow-editor" ? "flow_editor" : p === "alerts" ? "alerts" : p}`)}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 py-3 border-t border-slate-800 space-y-2">
        {/* Language switcher */}
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-500">{t("lang")}:</span>
          {LANGS.map((l) => (
            <button
              key={l.id}
              onClick={() => setLang(l.id as Lang)}
              className={`text-xs px-2 py-1 rounded ${lang === l.id ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-800"}`}
            >
              {l.id.toUpperCase()}
            </button>
          ))}
        </div>
        {/* Theme toggle */}
        <button
          onClick={toggle}
          className="w-full flex items-center justify-between px-3 py-2 rounded bg-slate-800 text-xs text-slate-300 hover:bg-slate-700 transition"
          title="Press T"
        >
          <span>{theme === "dark" ? t("theme_dark") : t("theme_light")}</span>
          <span className="text-base">{theme === "dark" ? "🌙" : "☀️"}</span>
        </button>
        <div className="text-xs text-slate-500 px-1">{t("portal")}</div>
      </div>
    </aside>
  );
}
