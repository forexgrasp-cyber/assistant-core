"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

type Toast = { id: number; text: string; kind: "success" | "error" | "info" };

const ToastCtx = createContext<{ toast: (text: string, kind?: Toast["kind"]) => void }>({
  toast: () => {},
});

let nextId = 1;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((text: string, kind: Toast["kind"] = "info") => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, text, kind }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
  }, []);

  return (
    <ToastCtx.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 w-80">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`animate-slide-up rounded-lg shadow-lg px-4 py-3 text-sm text-white ${
              t.kind === "error" ? "bg-red-600" : t.kind === "success" ? "bg-green-600" : "bg-slate-800"
            }`}
          >
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  return useContext(ToastCtx);
}
