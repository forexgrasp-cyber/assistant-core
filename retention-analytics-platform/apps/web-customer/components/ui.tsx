"use client";

import { useState } from "react";
import { useToast } from "./ToastProvider";
import { useI18n } from "./LangProvider";

export function CopyButton({ text, className = "" }: { text: string; className?: string }) {
  const { toast } = useToast();
  const { t } = useI18n();
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={async (e) => {
        e.stopPropagation();
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          toast(t("copied"), "success");
          setTimeout(() => setDone(false), 1500);
        } catch {
          toast("Copy failed", "error");
        }
      }}
      className={`text-xs text-gray-400 hover:text-indigo-600 ${className}`}
      title={t("copy")}
    >
      {done ? "✓" : "⧉"}
    </button>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function EmptyState({ text, hint }: { text: string; hint?: string }) {
  return (
    <div className="text-center py-10 text-gray-400">
      <p className="text-4xl mb-2">∅</p>
      <p className="text-sm font-medium">{text}</p>
      {hint && <p className="text-xs mt-1">{hint}</p>}
    </div>
  );
}
