import type { Metadata } from "next";
import AuthGate from "@/components/AuthGate";
import CommandPalette from "@/components/CommandPalette";
import Sidebar from "@/components/Sidebar";
import Tour from "@/components/Tour";

export const metadata: Metadata = {
  title: "Customer Portal",
  description:
    "Retention analytics for subscription businesses: campaigns, flows, customer health and measured outcomes.",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <div className="min-h-screen flex">
        <Sidebar />
        <main className="flex-1 p-8 overflow-y-auto">{children}</main>
      </div>
      <CommandPalette />
      <Tour />
    </AuthGate>
  );
}
