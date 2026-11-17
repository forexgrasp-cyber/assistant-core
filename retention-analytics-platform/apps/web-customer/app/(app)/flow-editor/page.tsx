"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import FlowCanvas, { FlowEdge, FlowNode } from "@/components/FlowCanvas";
import { useToast } from "@/components/ToastProvider";

export default function FlowEditorPage() {
  const { toast } = useToast();
  const [graphs, setGraphs] = useState<any[]>([]);
  const [current, setCurrent] = useState<any>(null);
  const [nodes, setNodes] = useState<FlowNode[]>([]);
  const [edges, setEdges] = useState<FlowEdge[]>([]);
  const [services, setServices] = useState<string[]>([]);
  const [trigger, setTrigger] = useState("");
  const [name, setName] = useState("");
  const [validation, setValidation] = useState<any>(null);

  const load = () => {
    apiGet("/flow-editor/graphs").then((d: any) => {
      setGraphs(d.graphs ?? []);
      if (d.graphs?.length && !current) open(d.graphs[0]);
    }).catch(() => {});
    apiGet("/services").then((d: any) => setServices((d.services ?? []).map((s: any) => s.name))).catch(() => {});
  };

  const open = (g: any) => {
    setCurrent(g);
    setNodes(g.nodes ?? []);
    setEdges(g.edges ?? []);
    setTrigger(g.trigger_event ?? "");
    setName(g.name ?? "");
    setValidation(null);
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!current) return;
    await apiPost(`/flow-editor/graphs/${current.graph_id}` ? "" : "", {}).catch(() => {});
    const res = await fetch(`/api/v1/flow-editor/graphs/${current.graph_id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Authorization: "Bearer dev-token" },
      body: JSON.stringify({ name, trigger_event: trigger, nodes, edges }),
    });
    if (res.ok) {
      toast("Flow saved", "success");
      load();
    } else {
      toast("Save failed: " + res.status, "error");
    }
  };

  const create = async () => {
    const r: any = await apiPost("/flow-editor/graphs", { name: "New flow", trigger_event: "client.created", nodes: [], edges: [] });
    toast("Flow created", "success");
    load();
    open(r.graph);
  };

  const validate = async () => {
    if (!current) return;
    const r: any = await apiPost(`/flow-editor/graphs/${current.graph_id}/validate`);
    setValidation(r);
  };

  const publish = async () => {
    if (!current) return;
    const r: any = await apiPost(`/flow-editor/graphs/${current.graph_id}/publish`);
    if (r.status === "published") {
      toast(`Published — workflow ${r.workflow.id} with ${r.workflow.steps.length} steps`, "success");
    } else {
      toast("Fix validation errors first: " + r.errors.join(", "), "error");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Flow Builder</h1>
          <p className="text-gray-500 text-sm mt-1">
            Visual automation canvas — drag nodes, connect them, validate, publish as a workflow.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={create} className="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">+ New flow</button>
          <button onClick={validate} className="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Validate</button>
          <button onClick={save} className="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Save</button>
          <button onClick={publish} className="px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Publish</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-3 space-y-1">
          <p className="text-xs font-semibold text-gray-400 uppercase mb-2">Flows</p>
          {graphs.map((g) => (
            <button key={g.graph_id} onClick={() => open(g)}
              className={`w-full text-left px-2 py-1.5 rounded text-xs font-mono ${current?.graph_id === g.graph_id ? "bg-indigo-50 text-indigo-700" : "hover:bg-gray-50"}`}>
              {g.name}
              <span className="block text-[10px] text-gray-400">{g.status} · {g.nodes?.length ?? 0} nodes</span>
            </button>
          ))}
          {graphs.length === 0 && <p className="text-xs text-gray-400">No flows yet.</p>}
        </div>

        <div className="lg:col-span-3 bg-white rounded-lg border border-gray-200 p-4">
          {current ? (
            <>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Flow name" className="border border-gray-300 rounded px-3 py-2 text-sm" />
                <input value={trigger} onChange={(e) => setTrigger(e.target.value)} placeholder="Trigger event (e.g. client.churn_risk)" className="border border-gray-300 rounded px-3 py-2 text-sm font-mono" />
              </div>
              <FlowCanvas nodes={nodes} edges={edges} onChange={(n, e) => { setNodes(n); setEdges(e); }} services={services} />
              {validation && (
                <div className={`mt-3 p-3 rounded text-sm ${validation.valid ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
                  {validation.valid ? "✓ Valid — ready to publish" : validation.errors.map((e: string) => `• ${e}`).join(" ")}
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-400 p-8 text-center">Create a flow to start building.</p>
          )}
        </div>
      </div>
    </div>
  );
}
