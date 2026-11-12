import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { LangProvider, useI18n } from "@/components/LangProvider";
import { ToastProvider } from "@/components/ToastProvider";
import CommandPalette from "@/components/CommandPalette";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Retention Analytics — Customer Portal",
  description:
    "Stop churn before it happens. Automated retention workflows, multi-channel campaigns, and real-time analytics — all wired through one platform.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <LangProvider>
          <ToastProvider>
            <div className="min-h-screen flex">
              <Sidebar />
              <main className="flex-1 p-8 overflow-y-auto">{children}</main>
            </div>
            <CommandPalette />
          </ToastProvider>
        </LangProvider>
      </body>
    </html>
  );
}
