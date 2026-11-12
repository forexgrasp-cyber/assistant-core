"use client";

import { useCallback, useRef, useState } from "react";

export interface FlowNode {
  id: string;
  type: "trigger" | "service" | "condition" | "end";
  service?: string;
  action?: string;
  label?: string;
  position: { x: number; y: number };
}

export interface FlowEdge {
  from: string;
  to: string;
}

interface Props {
  nodes: FlowNode[];
  edges: FlowEdge[];
  onChange: (nodes: FlowNode[], edges: FlowEdge[]) => void;
  services: string[];
  readOnly?: boolean;
}

const NODE_W = 168;
const NODE_H = 52;

const COLORS: Record<string, string> = {
  trigger: "#f59e0b",
  service: "#4f46e5",
  condition: "#0ea5e9",
  end: "#64748b",
};

export default function FlowCanvas({ nodes, edges, onChange, services, readOnly }: Props) {
  const [drag, setDrag] = useState<{ id: string; dx: number; dy: number } | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const toSvg = useCallback((e: React.MouseEvent) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const onNodeDown = (id: string) => (e: React.MouseEvent) => {
    if (readOnly) return;
    const p = toSvg(e);
    const n = nodes.find((x) => x.id === id);
    if (!n) return;
    setDrag({ id, dx: p.x - n.position.x, dy: p.y - n.position.y });
  };

  const onMove = (e: React.MouseEvent) => {
    if (!drag) return;
    const p = toSvg(e);
    onChange(
      nodes.map((n) => (n.id === drag.id ? { ...n, position: { x: p.x - drag.dx, y: p.y - drag.dy } } : n)),
      edges,
    );
  };

  const onNodeClick = (id: string) => (e: React.MouseEvent) => {
    if (readOnly) return;
    e.stopPropagation();
    if (connecting && connecting !== id) {
      onChange(nodes, [...edges, { from: connecting, to: id }]);
      setConnecting(null);
    } else {
      setConnecting(id);
    }
  };

  const onCanvasClick = () => setConnecting(null);

  const addNode = (type: FlowNode["type"]) => {
    const id = `n${Date.now().toString(36)}`;
    const node: FlowNode = {
      id, type, position: { x: 60 + (nodes.length % 4) * 200, y: 50 + Math.floor(nodes.length / 4) * 120 },
      service: type === "service" ? services[0] : undefined,
      action: type === "service" ? "send" : undefined,
      label: type === "trigger" ? "Trigger" : type === "end" ? "End" : undefined,
    };
    onChange([...nodes, node], edges);
  };

  const removeNode = (id: string) => {
    onChange(nodes.filter((n) => n.id !== id), edges.filter((e) => e.from !== id && e.to !== id));
  };

  const edgePath = (from: FlowNode, to: FlowNode) => {
    const x1 = from.position.x + NODE_W / 2;
    const y1 = from.position.y + NODE_H / 2;
    const x2 = to.position.x + NODE_W / 2;
    const y2 = to.position.y + NODE_H / 2;
    const mid = (y1 + y2) / 2;
    return `M ${x1} ${y1} C ${x1} ${mid}, ${x2} ${mid}, ${x2} ${y2}`;
  };

  return (
    <div className="relative">
      {!readOnly && (
        <div className="flex gap-2 mb-3 flex-wrap">
          <button onClick={() => addNode("trigger")} className="px-3 py-1.5 text-xs bg-amber-500 text-white rounded">+ Trigger</button>
          <button onClick={() => addNode("service")} className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded">+ Service</button>
          <button onClick={() => addNode("condition")} className="px-3 py-1.5 text-xs bg-sky-600 text-white rounded">+ Condition</button>
          <button onClick={() => addNode("end")} className="px-3 py-1.5 text-xs bg-slate-600 text-white rounded">+ End</button>
          {connecting && <span className="text-xs text-gray-500 self-center">Click a target node to connect…</span>}
        </div>
      )}
      <svg
        ref={svgRef}
        onMouseMove={onMove}
        onMouseUp={() => setDrag(null)}
        onClick={onCanvasClick}
        className="w-full bg-gray-50 dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-700 select-none"
        style={{ height: 420 }}
      >
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#94a3b8" />
          </marker>
        </defs>
        {edges.map((e, i) => {
          const from = nodes.find((n) => n.id === e.from);
          const to = nodes.find((n) => n.id === e.to);
          if (!from || !to) return null;
          return (
            <path key={i} d={edgePath(from, to)} stroke="#94a3b8" strokeWidth={2} fill="none" markerEnd="url(#arrow)" />
          );
        })}
        {nodes.map((n) => (
          <g
            key={n.id}
            transform={`translate(${n.position.x}, ${n.position.y})`}
            onMouseDown={onNodeDown(n.id)}
            onClick={onNodeClick(n.id)}
            style={{ cursor: readOnly ? "default" : "grab" }}
          >
            <rect width={NODE_W} height={NODE_H} rx={10} fill="var(--surface)" stroke={COLORS[n.type]} strokeWidth={connecting === n.id ? 3 : 2} />
            <rect width={5} height={NODE_H} rx={2} fill={COLORS[n.type]} />
            <text x={16} y={21} fontSize={12} fontWeight={600} fill="var(--text)">
              {n.type === "service" ? `${n.service}.${n.action}` : n.label || n.type}
            </text>
            <text x={16} y={38} fontSize={10} fill="var(--text-2)">
              {n.type === "service" ? n.service : n.type}
            </text>
            {!readOnly && (
              <circle
                cx={NODE_W - 12} cy={12} r={8} fill="#ef4444" opacity={0.85}
                onClick={(e) => { e.stopPropagation(); removeNode(n.id); }}
              >
                <title>Remove node</title>
              </circle>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}
