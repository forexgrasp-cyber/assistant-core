import type { Metadata } from "next";
import "./globals.css";
import { LangProvider } from "@/components/LangProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ToastProvider } from "@/components/ToastProvider";

export const metadata: Metadata = {
  title: {
    default: "Snapford Retention — Stop churn before it happens",
    template: "%s · Snapford Retention",
  },
  description:
    "Retention analytics for subscription businesses: automated campaigns, dunning, churn prediction, health scores and NPS — measured before and after.",
};

const THEME_BOOTSTRAP = `try{var s=localStorage.getItem('ra_theme');var t=(s==='dark'||s==='light')?s:(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.classList.toggle('dark',t==='dark');document.documentElement.style.colorScheme=t;}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="stylesheet" href="/api/seo/style/tokens.css" />
        <link rel="manifest" href="/api/seo/manifest" />
        <meta name="theme-color" content="#4f46e5" />
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body>
        <LangProvider>
          <ThemeProvider>
            <ToastProvider>{children}</ToastProvider>
          </ThemeProvider>
        </LangProvider>
      </body>
    </html>
  );
}
