import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Customer Portal — Retention Analytics",
  description: "Dashboards, campaigns, flows, reports for retention marketing",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="border-b border-gray-200 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
              <div className="flex items-center gap-2 font-bold text-gray-900">
                <span className="bg-indigo-600 text-white px-2 py-0.5 rounded text-xs">RA</span>
                <span>Retention Analytics</span>
              </div>
              <div className="flex items-center gap-4">
                <a href="/dashboard" className="text-sm font-medium text-gray-600 hover:text-indigo-600">
                  Dashboard
                </a>
                <a href="/campaigns" className="text-sm font-medium text-gray-600 hover:text-indigo-600">
                  Campaigns
                </a>
                <a href="/flows" className="text-sm font-medium text-gray-600 hover:text-indigo-600">
                  Flows
                </a>
                <a href="/reports" className="text-sm font-medium text-gray-600 hover:text-indigo-600">
                  Reports
                </a>
                <a href="/settings" className="text-sm font-medium text-gray-600 hover:text-indigo-600">
                  Settings
                </a>
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">{children}</main>
      </body>
    </html>
  );
}
