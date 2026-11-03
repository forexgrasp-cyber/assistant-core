import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Developer Console — Retention Analytics",
  description: "Schema builder, workflow designer, vertical packs, tenants",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="border-b border-gray-200 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
              <div className="flex items-center gap-2 font-bold text-gray-900">
                <span className="bg-slate-900 text-white px-2 py-0.5 rounded text-xs">DC</span>
                <span>Developer Console</span>
              </div>
              <div className="flex items-center gap-4">
                <a href="/" className="text-sm font-medium text-gray-600 hover:text-indigo-600">Overview</a>
                <a href="/schema" className="text-sm font-medium text-gray-600 hover:text-indigo-600">Schema Builder</a>
                <a href="/workflows" className="text-sm font-medium text-gray-600 hover:text-indigo-600">Workflows</a>
                <a href="/verticals" className="text-sm font-medium text-gray-600 hover:text-indigo-600">Vertical Packs</a>
                <a href="/tenants" className="text-sm font-medium text-gray-600 hover:text-indigo-600">Tenants</a>
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">{children}</main>
      </body>
    </html>
  );
}
