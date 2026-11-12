"""HTML rendering for human-facing endpoints.

Content negotiation: browsers (Accept: text/html) get a styled page;
API clients (Accept: application/json or no Accept) get raw JSON.
"""

from __future__ import annotations

import html
import json
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse


def wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


_PAGE_CSS = """
 body{font-family:system-ui,sans-serif;margin:0;background:#f8fafc;color:#0f172a}
 header{background:#0f172a;color:#fff;padding:18px 28px;display:flex;align-items:center;gap:14px}
 header h1{font-size:18px;margin:0}
 header .sub{color:#94a3b8;font-size:13px}
 header .ok{color:#34d399;font-weight:bold}
 nav{background:#fff;border-bottom:1px solid #e2e8f0;padding:8px 28px;font-size:13px}
 nav a{color:#4f46e5;text-decoration:none;margin-right:14px}
 main{max-width:1100px;margin:20px auto;padding:0 20px}
 .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:18px}
 .card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px}
 .card b{font-size:22px;display:block}
 .card span{font-size:11px;color:#64748b;text-transform:uppercase}
 section{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-bottom:16px}
 h2{font-size:14px;margin:0 0 10px;color:#334155;text-transform:uppercase;letter-spacing:.04em}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th{text-align:left;color:#64748b;font-size:11px;text-transform:uppercase;padding:5px 8px;border-bottom:2px solid #e2e8f0}
 td{padding:5px 8px;border-bottom:1px solid #f1f5f9;vertical-align:top}
 code{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px;color:#4f46e5}
 .chip{display:inline-block;background:#eef2ff;color:#4338ca;border-radius:6px;padding:2px 8px;margin:2px;font-size:11px;font-family:monospace}
 .bar{height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;min-width:80px}
 .bar>div{height:100%;background:#4f46e5}
 pre{background:#0f172a;color:#e2e8f0;padding:12px;border-radius:8px;overflow-x:auto;font-size:12px}
 .mono{font-family:ui-monospace,monospace;font-size:12px}
"""


def page(title: str, body: str, status: str = "ok") -> HTMLResponse:
    return HTMLResponse(f"""<!DOCTYPE html><html><head><meta charset='utf-8'/>
<meta name='viewport' content='width=device-width,initial-scale=1'/>
<title>{html.escape(title)} — Retention Analytics</title><style>{_PAGE_CSS}</style></head><body>
<header><h1>{html.escape(title)}</h1><span class='sub'>retention-analytics-platform</span><span class='ok'>● {status}</span></header>
<nav><a href='/'>Overview</a><a href='/health'>Health</a><a href='/metrics'>Metrics</a>
<a href='/api/v1/services'>Services</a><a href='/api/v1/workflows'>Workflows</a>
<a href='/api/v1/pains'>Pains</a><a href='/api/v1/help'>Help</a>
<a href='/api/v1/actions'>Actions</a><a href='/docs'>Swagger</a>
<a href='http://localhost:47320'>Customer portal</a><a href='http://localhost:47321'>Dev console</a></nav>
<main>{body}</main></body></html>""")


def json_to_table(data: Any, max_rows: int = 200) -> str:
    """Render arbitrary JSON as readable HTML (tables for lists of dicts, chips for scalars)."""
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = list(data[0].keys())[:8]
        rows = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(_short(v)))}</td>" for v in [r.get(k) for k in keys]) + "</tr>"
            for r in data[:max_rows]
        )
        head = "".join(f"<th>{html.escape(k)}</th>" for k in keys)
        return f"<table><tr>{head}</tr>{rows}</table><p class='mono' style='color:#64748b'>{len(data)} rows (showing {min(len(data), max_rows)})</p>"
    if isinstance(data, dict):
        rows = "".join(
            f"<tr><td><code>{html.escape(str(k))}</code></td><td>{html.escape(str(_short(v)))}</td></tr>"
            for k, v in list(data.items())[:max_rows]
        )
        return f"<table>{rows}</table>"
    return f"<pre>{html.escape(json.dumps(data, indent=2, default=str)[:4000])}</pre>"


def _short(v: Any) -> Any:
    s = str(v)
    return s[:80] + "…" if len(s) > 80 else s


def maybe_html(request: Request, data: Any, title: str, body_extra: str = "") -> Any:
    """Return HTMLResponse for browsers, raw data for API clients."""
    if wants_html(request):
        body = f"<section><h2>{html.escape(title)}</h2>{json_to_table(data)}{body_extra}</section>"
        return page(title, body)
    return data


def metrics_to_html(prom_text: str) -> HTMLResponse:
    """Render Prometheus text exposition as a human table, grouped by metric family."""
    families: dict[str, list[tuple[str, str]]] = {}
    for line in prom_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if " " in line:
            name_labels, value = line.rsplit(" ", 1)
            name = name_labels.split("{")[0]
            labels = name_labels[len(name):].strip("{}")
            families.setdefault(name, []).append((labels, value))
    sections = []
    for fam, samples in sorted(families.items()):
        rows = "".join(f"<tr><td class='mono'>{html.escape(lbl or '—')}</td><td><b>{html.escape(val)}</b></td></tr>" for lbl, val in samples[:50])
        sections.append(f"<section><h2>{html.escape(fam)} ({len(samples)})</h2><table>{rows}</table></section>")
    body = f"<p class='mono' style='color:#64748b'>{len(families)} metric families · raw exposition at <a href='/metrics?format=raw'><code>/metrics</code></a> for Prometheus scraping</p>" + "".join(sections)
    return page("Metrics", body)
