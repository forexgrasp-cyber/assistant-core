"use client";

import { useEffect, useState } from "react";

const KEY = "ra_tour_done";

const STEPS = [
  { sel: '[href="/dashboard"]', title: "Your command center", text: "Live metrics, workflows and alerts. Customize the layout with 'Customize layout'." },
  { sel: '[href="/campaigns"]', title: "Campaigns", text: "Goal + segment + flows + schedule + metrics. The campaign is the unit of work." },
  { sel: '[href="/flows"]', title: "Flows", text: "Reusable automations: event → steps → services. Every flow shows WHAT/WHEN/WHO/RESULT." },
  { sel: '[href="/flow-editor"]', title: "Flow Builder", text: "Drag nodes, connect them, validate and publish a workflow visually." },
  { sel: '[href="/customers"]', title: "Customers", text: "Your records. Import/export CSV, set a service interval and we compute next-due dates." },
  { sel: '[href="/integrations"]', title: "Integrations", text: "Connect Stripe, HubSpot, Salesforce, Zendesk, Mixpanel, Segment and sync their data in." },
  { sel: '[href="/help"]', title: "Help & demo", text: "Run the full demo end-to-end and read the per-feature guides. Press ⌘K to jump anywhere." },
];

export default function Tour() {
  const [step, setStep] = useState(-1);
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (localStorage.getItem(KEY)) return;
    const t = setTimeout(() => setStep(0), 900);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (step < 0) return;
    const el = document.querySelector(STEPS[step].sel) as HTMLElement | null;
    if (el) {
      setRect(el.getBoundingClientRect());
      el.scrollIntoView({ block: "center" });
    }
  }, [step]);

  if (step < 0 || step >= STEPS.length) return null;
  const s = STEPS[step];
  const top = rect ? Math.min(Math.max(rect.top - 130, 12), window.innerHeight - 190) : 100;
  const left = rect ? Math.min(Math.max(rect.left, 12), window.innerWidth - 340) : 24;

  const finish = () => {
    localStorage.setItem(KEY, "1");
    setStep(-1);
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={finish} />
      <div
        className="fixed z-50 w-80 bg-white rounded-xl shadow-2xl border border-gray-200 p-4 animate-fade-in"
        style={{ top, left }}
      >
        <p className="text-xs text-indigo-600 font-semibold">Step {step + 1} of {STEPS.length}</p>
        <h3 className="font-bold text-gray-900 mt-1">{s.title}</h3>
        <p className="text-sm text-gray-600 mt-1">{s.text}</p>
        <div className="flex justify-between mt-4">
          <button onClick={finish} className="text-xs text-gray-400 hover:underline">Skip tour</button>
          <div className="flex gap-2">
            {step > 0 && <button onClick={() => setStep(step - 1)} className="px-3 py-1.5 text-xs border border-gray-300 rounded">Back</button>}
            <button onClick={() => (step === STEPS.length - 1 ? finish() : setStep(step + 1))}
              className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded">
              {step === STEPS.length - 1 ? "Finish" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
