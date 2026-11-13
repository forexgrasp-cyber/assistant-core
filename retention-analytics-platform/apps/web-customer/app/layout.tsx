import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { LangProvider, useI18n } from "@/components/LangProvider";
import { ToastProvider } from "@/components/ToastProvider";
import CommandPalette from "@/components/CommandPalette";
import Sidebar from "@/components/Sidebar";
import Tour from "@/components/Tour";

export const metadata: Metadata = {
  title: "Snapford Retention — Customer Portal",
  description:
    "Retention analytics for subscription businesses: automated campaigns, dunning, churn prediction, health scores and NPS — measured before and after.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="stylesheet" href="/api/seo/style/tokens.css" />
        <link rel="manifest" href="/api/seo/manifest" />
        <meta name="theme-color" content="#4f46e5" />
      </head>
      <body>
        <LangProvider>
          <ToastProvider>
            <div className="min-h-screen flex">
              <Sidebar />
              <main className="flex-1 p-8 overflow-y-auto">{children}</main>
            </div>
            <CommandPalette />
            <Tour />
          </ToastProvider>
        </LangProvider>
      </body>
    </html>
  );
}
