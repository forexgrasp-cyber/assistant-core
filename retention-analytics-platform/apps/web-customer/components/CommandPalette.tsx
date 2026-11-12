"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "./LangProvider";

const PAGES = [
  "dashboard", "campaigns", "flows", "customers", "segments", "analytics",
  "growth", "experiments", "ops", "integrations", "events", "reports",
  "presets", "help", "settings",
];

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const router = useRouter();
  const { t } = useI18n();

  const items = useMemo(
    () => PAGES.map((p) => ({ href: `/${p}`, label: t(`nav_${p === "help" ? "help" : p}`) || p, raw: p })),
    [t]
  );

  const filtered = items.filter((i) => (i.label + " " + i.raw).toLowerCase().includes(q.toLowerCase()));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
        setQ("");
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-start justify-center pt-24" onClick={() => setOpen(false)}>
      <div className="animate-fade-in w-full max-w-lg bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-gray-200 overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && filtered[0]) {
              router.push(filtered[0].href);
              setOpen(false);
            }
          }}
          placeholder={t("search_placeholder")}
          className="w-full px-4 py-3 text-sm border-b border-gray-200 outline-none bg-transparent"
        />
        <div className="max-h-72 overflow-y-auto">
          {filtered.map((i) => (
            <button
              key={i.href}
              onClick={() => { router.push(i.href); setOpen(false); }}
              className="w-full text-left px-4 py-2.5 text-sm hover:bg-indigo-50 flex items-center justify-between"
            >
              <span>{i.label}</span>
              <span className="text-xs text-gray-400 font-mono">{i.href}</span>
            </button>
          ))}
          {filtered.length === 0 && <p className="px-4 py-6 text-sm text-gray-400 text-center">{t("empty")}</p>}
        </div>
      </div>
    </div>
  );
}
