"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { Lang, getLang, setLang as persistLang, t as translate, DICTS } from "@/lib/i18n";

const LangCtx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (k: string) => string }>({
  lang: "en",
  setLang: () => {},
  t: (k) => k,
});

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    setLangState(getLang());
  }, []);

  const setLang = (l: Lang) => {
    setLangState(l);
    persistLang(l);
  };

  return (
    <LangCtx.Provider value={{ lang, setLang, t: (k) => translate(lang, k) }}>
      {children}
    </LangCtx.Provider>
  );
}

export function useI18n() {
  return useContext(LangCtx);
}
