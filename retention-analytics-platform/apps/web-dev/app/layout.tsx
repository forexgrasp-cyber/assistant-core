import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Developer Console — Retention Analytics Platform",
  description:
    "Explore the platform: 24 services, 4 workflows, 41 API endpoints. Invoke actions, run pipelines, inspect entities.",
};

const nav = [
  { href: "/", label: "Overview" },
  { href: "/services", label: "Services" },
  { href: "/workflows", label: "Workflows" },
  { href: "/api-explorer", label: "API Explorer" },
  { href: "/schema", label: "Entities" },
  { href: "/verticals", label: "Verticals" },
  { href: "/tenants", label: "Tenants" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex">
          <aside className="w-56 bg-slate-950 text-slate-300 flex flex-col">
            <div className="h-16 flex items-center px-5 border-b border-slate-800">
              <Link href="/" className="flex items-center gap-2 font-bold text-white">
                <span className="bg-emerald-500 text-white px-2 py-0.5 rounded text-xs">DC</span>
                <span className="text-sm">Dev Console</span>
              </Link>
            </div>
            <nav className="flex-1 px-3 py-4 space-y-1">
              {nav.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="block px-3 py-2 rounded text-sm font-medium hover:bg-slate-800 hover:text-white transition"
                >
                  {n.label}
                </Link>
              ))}
            </nav>
            <div className="px-5 py-4 border-t border-slate-800">
              <a href="http://127.0.0.1:47319/docs" target="_blank" className="text-xs text-emerald-400 hover:underline">
                Swagger UI ↗
              </a>
            </div>
          </aside>
          <main className="flex-1 p-8 overflow-y-auto bg-gray-50">{children}</main>
        </div>
      </body>
    </html>
  );
}
