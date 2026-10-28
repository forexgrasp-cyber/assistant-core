"""
Template Registry and Base Templates

Manages report templates, widget templates, and Jinja2 environment.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape, BaseLoader

from .models import ReportTemplate, WidgetDefinition, WidgetConfig, WidgetType


class TemplateRegistry:
    """Registry for report and widget templates."""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml', 'jinja2']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Custom filters
        self.env.filters['format_currency'] = self._format_currency
        self.env.filters['format_number'] = self._format_number
        self.env.filters['format_percent'] = self._format_percent
        self.env.filters['format_date'] = self._format_date
        self.env.filters['to_json'] = json.dumps
        
        # Registered templates
        self._report_templates: Dict[str, ReportTemplate] = {}
        self._widget_templates: Dict[WidgetType, str] = {}  # WidgetType -> template name
        
        # Load built-in widget templates
        self._register_builtin_widget_templates()

    def _register_builtin_widget_templates(self):
        """Register default widget templates."""
        self._widget_templates = {
            WidgetType.KPI_CARD: "widgets/kpi_card.html",
            WidgetType.METRIC_CARD: "widgets/metric_card.html",
            WidgetType.LINE_CHART: "widgets/line_chart.html",
            WidgetType.BAR_CHART: "widgets/bar_chart.html",
            WidgetType.AREA_CHART: "widgets/area_chart.html",
            WidgetType.PIE_CHART: "widgets/pie_chart.html",
            WidgetType.DONUT_CHART: "widgets/donut_chart.html",
            WidgetType.DATA_TABLE: "widgets/data_table.html",
            WidgetType.PIVOT_TABLE: "widgets/pivot_table.html",
            WidgetType.SUMMARY_TABLE: "widgets/summary_table.html",
            WidgetType.MARKDOWN: "widgets/markdown.html",
            WidgetType.TEXT_BLOCK: "widgets/text_block.html",
            WidgetType.AI_SUMMARY: "widgets/ai_summary.html",
            WidgetType.FUNNEL_CHART: "widgets/funnel_chart.html",
            WidgetType.COHORT_HEATMAP: "widgets/cohort_heatmap.html",
            WidgetType.HEATMAP: "widgets/heatmap.html",
            WidgetType.GAUGE: "widgets/gauge.html",
            WidgetType.PROGRESS_BAR: "widgets/progress_bar.html",
        }

    def register(self, template: ReportTemplate):
        """Register a report template."""
        self._report_templates[template.id] = template

    def get_report_template(self, template_id: str) -> Optional[ReportTemplate]:
        return self._report_templates.get(template_id)

    def get_widget_template(self, widget_type: WidgetType) -> Optional[str]:
        """Get template name for widget type."""
        return self._widget_templates.get(widget_type)

    def render_widget(self, widget_type: WidgetType, context: Dict[str, Any]) -> str:
        """Render a widget using its template."""
        template_name = self.get_widget_template(widget_type)
        if not template_name:
            return self._render_fallback(widget_type, context)
        
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception:
            return self._render_fallback(widget_type, context)

    def render_report(self, template: ReportTemplate, context: Dict[str, Any]) -> str:
        """Render a full report using a template."""
        template_name = f"reports/{template.id}.html"
        
        try:
            tmpl = self.env.get_template(template_name)
        except Exception:
            # Use default report template
            tmpl = self.env.get_template("reports/default.html")
        
        return tmpl.render(template=template, **context)

    def _render_fallback(self, widget_type: WidgetType, context: Dict[str, Any]) -> str:
        """Fallback rendering when template not found."""
        title = context.get('title', 'Widget')
        data = context.get('data', [])
        
        if widget_type in (WidgetType.KPI_CARD, WidgetType.METRIC_CARD):
            value = context.get('value', 'N/A')
            trend = context.get('trend')
            return f"""
            <div class="kpi-card">
                <h3>{title}</h3>
                <div class="value">{value}</div>
                {f'<div class="trend">{trend}</div>' if trend else ''}
            </div>
            """
        elif widget_type == WidgetType.DATA_TABLE:
            if not data:
                return f"<div class='widget'><h3>{title}</h3><p>No data</p></div>"
            
            headers = list(data[0].keys()) if data else []
            rows_html = ""
            for row in data:
                cells = "".join(f"<td>{row.get(h, '')}</td>" for h in headers)
                rows_html += f"<tr>{cells}</tr>"
            
            headers_html = "".join(f"<th>{h}</th>" for h in headers)
            return f"""
            <div class="widget data-table">
                <h3>{title}</h3>
                <table>
                    <thead><tr>{headers_html}</tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            """
        elif widget_type == WidgetType.MARKDOWN:
            content = context.get('content', '')
            # Simple markdown to HTML (would use markdown library in production)
            return f"<div class='widget markdown'>{content}</div>"
        
        return f"<div class='widget'><h3>{title}</h3><pre>{json.dumps(context, default=str, indent=2)}</pre></div>"

    def _format_currency(self, value: Any, currency: str = "USD", decimals: int = 2) -> str:
        """Format value as currency."""
        try:
            num = float(value)
            if currency == "USD":
                return f"${num:,.{decimals}f}"
            return f"{num:,.{decimals}f} {currency}"
        except (TypeError, ValueError):
            return str(value)

    def _format_number(self, value: Any, decimals: int = 0) -> str:
        """Format value as number with commas."""
        try:
            num = float(value)
            if decimals == 0:
                return f"{num:,.0f}"
            return f"{num:,.{decimals}f}"
        except (TypeError, ValueError):
            return str(value)

    def _format_percent(self, value: Any, decimals: int = 1) -> str:
        """Format value as percentage."""
        try:
            num = float(value)
            return f"{num:.{decimals}f}%"
        except (TypeError, ValueError):
            return str(value)

    def _format_date(self, value: Any, format: str = "%Y-%m-%d") -> str:
        """Format date value."""
        from datetime import datetime, date
        if isinstance(value, (datetime, date)):
            return value.strftime(format)
        try:
            return datetime.fromisoformat(str(value)).strftime(format)
        except (TypeError, ValueError):
            return str(value)


class BaseTemplate:
    """Base class for custom report templates."""

    def __init__(self, registry: TemplateRegistry):
        self.registry = registry

    def render_section(self, section, context: Dict[str, Any]) -> str:
        """Render a report section."""
        widgets_html = ""
        for widget in section.widgets:
            widgets_html += self.registry.render_widget(widget.config.type, {
                "title": widget.config.title,
                "data": context.get(widget.id, []),
                **widget.config.options,
            })
        
        return f"""
        <section class="report-section" id="{section.id}">
            <h2>{section.title}</h2>
            <div class="widgets-grid">
                {widgets_html}
            </div>
        </section>
        """

    def render_page(self, report_template: ReportTemplate, context: Dict[str, Any]) -> str:
        """Render full report page."""
        sections_html = ""
        for section in report_template.sections:
            sections_html += self.render_section(section, context)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report_template.name}</title>
            <meta charset="utf-8">
            <style>{self.get_styles()}</style>
        </head>
        <body>
            <header class="report-header">
                <h1>{report_template.name}</h1>
                <div class="report-meta">
                    Generated: {context.get('generated_at', '')}
                    Date Range: {context.get('date_range', '')}
                </div>
            </header>
            <main class="report-body">
                {sections_html}
            </main>
            <footer class="report-footer">
                <p>Confidential - For Internal Use Only</p>
            </footer>
        </body>
        </html>
        """

    def get_styles(self) -> str:
        """Get CSS styles for the template."""
        return """
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; color: #1a1a1a; line-height: 1.5; }
        .report-header { border-bottom: 2px solid #e5e7eb; padding-bottom: 20px; margin-bottom: 30px; }
        .report-header h1 { margin: 0 0 10px; font-size: 28px; font-weight: 700; }
        .report-meta { color: #6b7280; font-size: 14px; }
        .report-body { display: flex; flex-direction: column; gap: 30px; }
        .report-section h2 { font-size: 20px; font-weight: 600; margin: 0 0 16px; padding-bottom: 8px; border-bottom: 1px solid #e5e7eb; }
        .widgets-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
        .widget { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
        .widget h3 { margin: 0 0 12px; font-size: 14px; font-weight: 600; color: #374151; }
        .kpi-card .value { font-size: 32px; font-weight: 700; color: #111827; }
        .kpi-card .trend { font-size: 12px; color: #059669; }
        .data-table { overflow-x: auto; }
        .data-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .data-table th, .data-table td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }
        .data-table th { font-weight: 600; color: #374151; background: #f9fafb; }
        .report-footer { border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 40px; text-align: center; color: #9ca3af; font-size: 12px; }
        @media print {
            .widgets-grid { grid-template-columns: repeat(6, 1fr); }
            .widget { break-inside: avoid; }
            .report-header, .report-footer { display: none; }
        }
        """


# Default widget templates would be stored as files in template_dir/widgets/
# For now, the fallback rendering handles them