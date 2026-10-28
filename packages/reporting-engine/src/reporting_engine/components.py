"""
Component Renderers

Renders widgets to HTML/JSON for export. Supports charts (Plotly), tables, KPI cards, etc.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

from .models import (
    WidgetDefinition,
    WidgetConfig,
    WidgetType,
    DataSourceConfig,
    DataSourceType,
    QueryResult,
    RenderedWidget,
    ReportContext,
)


class WidgetRenderer:
    """Main widget renderer that dispatches to specialized renderers."""

    def __init__(self, engine):
        self.engine = engine
        self.chart_renderer = ChartRenderer()
        self.table_renderer = TableRenderer()

    async def render(self, widget: WidgetDefinition, context: ReportContext) -> RenderedWidget:
        """Render a widget to HTML and data."""
        start_time = datetime.utcnow()
        config = widget.config
        
        # Get data from context cache
        query_result = context.data_cache.get(widget.id)
        if not query_result:
            return RenderedWidget(
                widget_id=widget.id,
                type=config.type,
                title=config.title,
                errors=["No data available for widget"],
            )
        
        data = query_result.data
        render_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Dispatch to appropriate renderer
        try:
            if config.type in (WidgetType.LINE_CHART, WidgetType.BAR_CHART, WidgetType.AREA_CHART,
                              WidgetType.PIE_CHART, WidgetType.DONUT_CHART, WidgetType.SCATTER_PLOT,
                              WidgetType.FUNNEL_CHART, WidgetType.COHORT_HEATMAP, WidgetType.HEATMAP,
                              WidgetType.GAUGE):
                html, chart_config = await self.chart_renderer.render(config, data, query_result.columns)
                return RenderedWidget(
                    widget_id=widget.id,
                    type=config.type,
                    title=config.title,
                    html=html,
                    chart_config=chart_config,
                    render_time_ms=render_time_ms,
                    data_rows=len(data),
                )
            
            elif config.type in (WidgetType.DATA_TABLE, WidgetType.PIVOT_TABLE, WidgetType.SUMMARY_TABLE):
                html = self.table_renderer.render(config, data, query_result.columns)
                return RenderedWidget(
                    widget_id=widget.id,
                    type=config.type,
                    title=config.title,
                    html=html,
                    data=data,
                    render_time_ms=render_time_ms,
                    data_rows=len(data),
                )
            
            elif config.type in (WidgetType.KPI_CARD, WidgetType.METRIC_CARD):
                html = self._render_kpi_card(config, data)
                return RenderedWidget(
                    widget_id=widget.id,
                    type=config.type,
                    title=config.title,
                    html=html,
                    data=data[:1],
                    render_time_ms=render_time_ms,
                    data_rows=len(data),
                )
            
            elif config.type == WidgetType.MARKDOWN:
                html = self._render_markdown(config, data)
                return RenderedWidget(
                    widget_id=widget.id,
                    type=config.type,
                    title=config.title,
                    html=html,
                    render_time_ms=render_time_ms,
                )
            
            elif config.type == WidgetType.TEXT_BLOCK:
                html = self._render_text_block(config, data)
                return RenderedWidget(
                    widget_id=widget.id,
                    type=config.type,
                    title=config.title,
                    html=html,
                    render_time_ms=render_time_ms,
                )
            
            elif config.type == WidgetType.AI_SUMMARY:
                html = await self._render_ai_summary(config, data, context)
                return RenderedWidget(
                    widget_id=widget.id,
                    type=config.type,
                    title=config.title,
                    html=html,
                    render_time_ms=render_time_ms,
                )
            
            else:
                # Fallback: render as JSON
                html = self._render_json(config, data)
                return RenderedWidget(
                    widget_id=widget.id,
                    type=config.type,
                    title=config.title,
                    html=html,
                    data=data,
                    render_time_ms=render_time_ms,
                    data_rows=len(data),
                )
                
        except Exception as e:
            return RenderedWidget(
                widget_id=widget.id,
                type=config.type,
                title=config.title,
                errors=[f"Render failed: {str(e)}"],
                render_time_ms=render_time_ms,
            )

    def _render_kpi_card(self, config: WidgetConfig, data: List[Dict[str, Any]]) -> str:
        """Render KPI/Metric card."""
        options = config.options
        format_type = options.get("format", "number")
        trend = options.get("trend", False)
        prominent = options.get("prominent", False)
        
        value = "N/A"
        if data:
            # Get first metric value
            for metric in config.data_source.metrics:
                if metric in data[0]:
                    value = self._format_value(data[0][metric], format_type)
                    break
        
        trend_html = ""
        if trend and len(data) >= 2:
            # Calculate trend from last two periods
            current = data[0].get(config.data_source.metrics[0], 0) if config.data_source.metrics else 0
            previous = data[1].get(config.data_source.metrics[0], 0) if config.data_source.metrics else 0
            if previous:
                pct = ((current - previous) / abs(previous)) * 100
                trend_class = "positive" if pct >= 0 else "negative"
                trend_html = f'<span class="trend {trend_class}">{pct:+.1f}%</span>'
        
        card_class = "kpi-card prominent" if prominent else "kpi-card"
        
        return f"""
        <div class="{card_class}">
            <h3>{config.title}</h3>
            <div class="value">{value}</div>
            {trend_html}
            <div class="subtitle">{config.subtitle or ''}</div>
        </div>
        """

    def _render_markdown(self, config: WidgetConfig, data: List[Dict[str, Any]]) -> str:
        """Render markdown content."""
        content = config.options.get("content", "")
        # Would use markdown library in production
        return f'<div class="widget markdown">{content}</div>'

    def _render_text_block(self, config: WidgetConfig, data: List[Dict[str, Any]]) -> str:
        """Render text block."""
        content = config.options.get("content", "")
        return f'<div class="widget text-block">{content}</div>'

    async def _render_ai_summary(self, config: WidgetConfig, data: List[Dict[str, Any]], context: ReportContext) -> str:
        """Render AI-generated summary."""
        if not self.engine.ai_service:
            return '<div class="widget ai-summary"><p>AI service not available</p></div>'
        
        prompt = config.ai_prompt or f"""
        Summarize this data for a business report:
        {json.dumps(data[:10], default=str, indent=2)}
        Focus on key insights and trends.
        """
        
        try:
            response = await self.engine.ai_service.generate(prompt)
            return f'<div class="widget ai-summary"><div class="ai-content">{response.text}</div></div>'
        except Exception as e:
            return f'<div class="widget ai-summary"><p>AI summary failed: {str(e)}</p></div>'

    def _render_json(self, config: WidgetConfig, data: List[Dict[str, Any]]) -> str:
        """Render as formatted JSON."""
        return f'<pre class="widget json-view">{json.dumps(data, default=str, indent=2)}</pre>'

    def _format_value(self, value: Any, format_type: str) -> str:
        """Format value based on type."""
        try:
            if format_type == "currency":
                return f"${float(value):,.2f}"
            elif format_type == "number":
                return f"{float(value):,.0f}"
            elif format_type == "percent":
                return f"{float(value):.1f}%"
            elif format_type == "ratio":
                return f"{float(value):.2f}x"
            else:
                return str(value)
        except (TypeError, ValueError):
            return str(value)


class ChartRenderer:
    """Renders charts using Plotly."""

    def __init__(self):
        self.default_layout = {
            "font": {"family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif", "size": 12},
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
            "xaxis": {"showgrid": True, "gridcolor": "#f3f4f6", "zeroline": False},
            "yaxis": {"showgrid": True, "gridcolor": "#f3f4f6", "zeroline": False},
            "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
            "hovermode": "x unified",
        }

    async def render(
        self,
        config: WidgetConfig,
        data: List[Dict[str, Any]],
        columns: List[str],
    ) -> tuple[str, Dict[str, Any]]:
        """Render chart and return HTML div + chart config."""
        options = config.options
        chart_type = config.type
        
        if not data:
            return self._empty_chart(config.title), {}
        
        # Prepare data
        x_field = options.get("x_axis", columns[0] if columns else "date")
        y_fields = options.get("series", config.data_source.metrics)
        if isinstance(y_fields, str):
            y_fields = [y_fields]
        
        # Create figure based on type
        if chart_type == WidgetType.LINE_CHART:
            fig = self._create_line_chart(data, x_field, y_fields, options)
        elif chart_type == WidgetType.BAR_CHART:
            fig = self._create_bar_chart(data, x_field, y_fields, options)
        elif chart_type == WidgetType.AREA_CHART:
            fig = self._create_area_chart(data, x_field, y_fields, options)
        elif chart_type == WidgetType.PIE_CHART:
            fig = self._create_pie_chart(data, options)
        elif chart_type == WidgetType.DONUT_CHART:
            fig = self._create_donut_chart(data, options)
        elif chart_type == WidgetType.SCATTER_PLOT:
            fig = self._create_scatter_plot(data, options)
        elif chart_type == WidgetType.FUNNEL_CHART:
            fig = self._create_funnel_chart(data, options)
        elif chart_type == WidgetType.COHORT_HEATMAP:
            fig = self._create_cohort_heatmap(data, options)
        elif chart_type == WidgetType.HEATMAP:
            fig = self._create_heatmap(data, options)
        elif chart_type == WidgetType.GAUGE:
            fig = self._create_gauge(data, options)
        else:
            fig = self._create_line_chart(data, x_field, y_fields, options)
        
        # Apply common layout
        fig.update_layout(
            title={"text": config.title, "x": 0.02, "xanchor": "left"},
            **self.default_layout,
        )
        
        # Apply custom options
        if options.get("height"):
            fig.update_layout(height=options["height"])
        
        # Generate HTML div
        html = fig.to_html(
            include_plotlyjs="cdn",
            div_id=f"chart-{uuid.uuid4().hex[:8]}",
            config={"displayModeBar": False, "responsive": True},
        )
        
        # Extract chart config for re-rendering
        chart_config = {
            "type": chart_type.value,
            "data": [trace.to_plotly_json() for trace in fig.data],
            "layout": fig.layout.to_plotly_json(),
        }
        
        return html, chart_config

    def _empty_chart(self, title: str) -> str:
        return f'<div class="chart-empty"><p>No data available for {title}</p></div>'

    def _create_line_chart(self, data: List[Dict], x_field: str, y_fields: List[str], options: Dict) -> go.Figure:
        fig = go.Figure()
        
        for i, y_field in enumerate(y_fields):
            x_vals = [row.get(x_field) for row in data]
            y_vals = [row.get(y_field, 0) for row in data]
            
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines+markers",
                name=y_field.replace("_", " ").title(),
                line={"width": 2},
                marker={"size": 4},
            ))
        
        if options.get("stacked"):
            fig.update_layout(yaxis={"type": "linear"})
        
        return fig

    def _create_bar_chart(self, data: List[Dict], x_field: str, y_fields: List[str], options: Dict) -> go.Figure:
        fig = go.Figure()
        
        stacked = options.get("stacked", False)
        
        for i, y_field in enumerate(y_fields):
            x_vals = [row.get(x_field) for row in data]
            y_vals = [row.get(y_field, 0) for row in data]
            
            fig.add_trace(go.Bar(
                x=x_vals,
                y=y_vals,
                name=y_field.replace("_", " ").title(),
                marker={"color": self._get_color(i)},
            ))
        
        if stacked:
            fig.update_layout(barmode="stack")
        else:
            fig.update_layout(barmode="group")
        
        return fig

    def _create_area_chart(self, data: List[Dict], x_field: str, y_fields: List[str], options: Dict) -> go.Figure:
        fig = go.Figure()
        
        for i, y_field in enumerate(y_fields):
            x_vals = [row.get(x_field) for row in data]
            y_vals = [row.get(y_field, 0) for row in data]
            
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines",
                fill="tonexty" if i > 0 else "tozeroy",
                name=y_field.replace("_", " ").title(),
                line={"width": 1, "color": self._get_color(i)},
                fillcolor=self._get_fill_color(i),
            ))
        
        fig.update_layout(barmode="stack" if options.get("stacked") else "overlay")
        return fig

    def _create_pie_chart(self, data: List[Dict], options: Dict) -> go.Figure:
        labels_field = options.get("labels", "label")
        values_field = options.get("values", "value")
        
        labels = [row.get(labels_field, f"Item {i}") for i, row in enumerate(data)]
        values = [row.get(values_field, 0) for row in data]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0,
            textinfo="label+percent",
            textposition="inside",
            marker={"colors": [self._get_color(i) for i in range(len(labels))]},
        )])
        
        return fig

    def _create_donut_chart(self, data: List[Dict], options: Dict) -> go.Figure:
        fig = self._create_pie_chart(data, options)
        fig.data[0].hole = 0.6
        return fig

    def _create_scatter_plot(self, data: List[Dict], options: Dict) -> go.Figure:
        x_field = options.get("x", "x")
        y_field = options.get("y", "y")
        color_field = options.get("color")
        size_field = options.get("size")
        
        fig = go.Figure()
        
        if color_field:
            # Group by color field
            groups = {}
            for row in data:
                color_val = row.get(color_field, "default")
                if color_val not in groups:
                    groups[color_val] = {"x": [], "y": [], "size": []}
                groups[color_val]["x"].append(row.get(x_field))
                groups[color_val]["y"].append(row.get(y_field))
                if size_field:
                    groups[color_val]["size"].append(row.get(size_field, 10))
            
            for i, (color_val, vals) in enumerate(groups.items()):
                fig.add_trace(go.Scatter(
                    x=vals["x"],
                    y=vals["y"],
                    mode="markers",
                    name=str(color_val),
                    marker={
                        "size": vals["size"] if size_field else 10,
                        "color": self._get_color(i),
                        "opacity": 0.7,
                    },
                ))
        else:
            fig.add_trace(go.Scatter(
                x=[row.get(x_field) for row in data],
                y=[row.get(y_field) for row in data],
                mode="markers",
                marker={"size": 10, "color": self._get_color(0), "opacity": 0.7},
            ))
        
        return fig

    def _create_funnel_chart(self, data: List[Dict], options: Dict) -> go.Figure:
        stages = options.get("stages", [])
        if not stages and data:
            stages = list(data[0].keys())
        
        values = []
        labels = []
        for stage in stages:
            if data:
                val = data[0].get(stage, 0)
            else:
                val = 0
            values.append(val)
            labels.append(stage.replace("_", " ").title())
        
        fig = go.Figure(go.Funnel(
            y=labels,
            x=values,
            textinfo="value+percent initial",
            marker={"color": [self._get_color(i) for i in range(len(labels))]},
        ))
        
        return fig

    def _create_cohort_heatmap(self, data: List[Dict], options: Dict) -> go.Figure:
        cohort_axis = options.get("cohort_axis", "cohort_month")
        period_axis = options.get("period_axis", "period")
        value_field = options.get("value", "repeat_rate")
        
        # Pivot data
        cohorts = sorted(set(row.get(cohort_axis) for row in data if row.get(cohort_axis)))
        periods = sorted(set(row.get(period_axis) for row in data if row.get(period_axis)))
        
        z = []
        for cohort in cohorts:
            row_vals = []
            for period in periods:
                val = 0
                for row in data:
                    if row.get(cohort_axis) == cohort and row.get(period_axis) == period:
                        val = row.get(value_field, 0)
                        break
                row_vals.append(val)
            z.append(row_vals)
        
        fig = go.Figure(data=go.Heatmap(
            z=z,
            x=[str(p) for p in periods],
            y=[str(c) for c in cohorts],
            colorscale="Blues",
            text=[[f"{v:.1%}" if v > 1 else f"{v:.1%}" for v in row] for row in z],
            texttemplate="%{text}",
            textfont={"size": 10},
            colorbar={"title": value_field.replace("_", " ").title()},
        ))
        
        fig.update_layout(
            xaxis_title="Period",
            yaxis_title="Cohort",
            yaxis={"autorange": "reversed"},
        )
        
        return fig

    def _create_heatmap(self, data: List[Dict], options: Dict) -> go.Figure:
        x_field = options.get("x", "x")
        y_field = options.get("y", "y")
        z_field = options.get("z", "value")
        
        # Pivot
        x_vals = sorted(set(row.get(x_field) for row in data))
        y_vals = sorted(set(row.get(y_field) for row in data))
        
        z = []
        for y in y_vals:
            row_vals = []
            for x in x_vals:
                val = 0
                for row in data:
                    if row.get(x_field) == x and row.get(y_field) == y:
                        val = row.get(z_field, 0)
                        break
                row_vals.append(val)
            z.append(row_vals)
        
        fig = go.Figure(data=go.Heatmap(
            z=z,
            x=[str(v) for v in x_vals],
            y=[str(v) for v in y_vals],
            colorscale=options.get("colorscale", "Viridis"),
        ))
        
        return fig

    def _create_gauge(self, data: List[Dict], options: Dict) -> go.Figure:
        value = data[0].get(options.get("value_field", "value"), 0) if data else 0
        max_val = options.get("max", 100)
        min_val = options.get("min", 0)
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": options.get("title", "")},
            delta={"reference": options.get("target", max_val * 0.8)},
            gauge={
                "axis": {"range": [min_val, max_val]},
                "bar": {"color": self._get_color(0)},
                "steps": [
                    {"range": [min_val, max_val * 0.5], "color": "#fee2e2"},
                    {"range": [max_val * 0.5, max_val * 0.8], "color": "#fef3c7"},
                    {"range": [max_val * 0.8, max_val], "color": "#dcfce7"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": options.get("target", max_val * 0.8),
                },
            },
        ))
        
        return fig

    def _get_color(self, index: int) -> str:
        colors = [
            "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
            "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
            "#f97316", "#6366f1", "#14b8a6", "#eab308",
        ]
        return colors[index % len(colors)]

    def _get_fill_color(self, index: int) -> str:
        colors = [
            "rgba(59, 130, 246, 0.2)",
            "rgba(16, 185, 129, 0.2)",
            "rgba(245, 158, 11, 0.2)",
            "rgba(239, 68, 68, 0.2)",
        ]
        return colors[index % len(colors)]


class TableRenderer:
    """Renders data tables with sorting, pagination, formatting."""

    def __init__(self):
        self.default_options = {
            "page_size": 25,
            "sortable": True,
            "filterable": True,
            "exportable": True,
            "striped": True,
            "hoverable": True,
            "compact": False,
        }

    def render(
        self,
        config: WidgetConfig,
        data: List[Dict[str, Any]],
        columns: List[str],
    ) -> str:
        """Render data table HTML."""
        options = {**self.default_options, **config.options}
        
        if not data:
            return f'<div class="widget table-empty"><p>No data available for {config.title}</p></div>'
        
        # Determine columns to show
        show_columns = options.get("columns", columns)
        if isinstance(show_columns, str):
            show_columns = [show_columns]
        
        # Format columns
        formatted_headers = []
        for col in show_columns:
            formatted_headers.append({
                "key": col,
                "label": col.replace("_", " ").title(),
                "format": self._get_column_format(col, options),
            })
        
        # Build table
        table_id = f"table-{uuid.uuid4().hex[:8]}"
        
        thead = "".join(
            f'<th data-key="{h["key"]}" data-format="{h["format"]}">{h["label"]}</th>'
            for h in formatted_headers
        )
        
        tbody_rows = []
        for row in data:
            cells = []
            for h in formatted_headers:
                val = row.get(h["key"], "")
                formatted = self._format_cell(val, h["format"])
                cells.append(f'<td data-key="{h["key"]}">{formatted}</td>')
            tbody_rows.append(f"<tr>{''.join(cells)}</tr>")
        
        tbody = "".join(tbody_rows)
        
        table_class = "data-table"
        if options.get("striped"):
            table_class += " striped"
        if options.get("hoverable"):
            table_class += " hoverable"
        if options.get("compact"):
            table_class += " compact"
        
        # Add toolbar
        toolbar = ""
        if options.get("exportable"):
            toolbar += '<button class="btn-export" data-format="csv">CSV</button>'
            toolbar += '<button class="btn-export" data-format="json">JSON</button>'
        
        return f"""
        <div class="widget data-table-widget" id="{table_id}">
            <div class="table-toolbar">{toolbar}</div>
            <div class="table-container">
                <table class="{table_class}">
                    <thead><tr>{thead}</tr></thead>
                    <tbody>{tbody}</tbody>
                </table>
            </div>
            {self._render_pagination(len(data), options) if len(data) > options.get("page_size", 25) else ""}
        </div>
        """

    def _get_column_format(self, column: str, options: Dict) -> str:
        """Determine format for column."""
        formats = options.get("column_formats", {})
        if column in formats:
            return formats[column]
        
        # Auto-detect
        if any(kw in column.lower() for kw in ["revenue", "amount", "price", "cost", "value", "ltv", "mrr"]):
            return "currency"
        elif any(kw in column.lower() for kw in ["rate", "pct", "percent", "percentage"]):
            return "percent"
        elif any(kw in column.lower() for kw in ["count", "number", "total", "orders", "sales", "units"]):
            return "number"
        elif any(kw in column.lower() for kw in ["date", "time", "created", "updated"]):
            return "date"
        return "auto"

    def _format_cell(self, value: Any, format_type: str) -> str:
        """Format cell value."""
        if value is None:
            return ""
        
        try:
            if format_type == "currency":
                return f"${float(value):,.2f}"
            elif format_type == "number":
                return f"{float(value):,.0f}"
            elif format_type == "percent":
                return f"{float(value):.1f}%"
            elif format_type == "date":
                from datetime import datetime
                if isinstance(value, (datetime,)):
                    return value.strftime("%Y-%m-%d")
                try:
                    return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d")
                except:
                    return str(value)
            elif format_type == "datetime":
                from datetime import datetime
                if isinstance(value, (datetime,)):
                    return value.strftime("%Y-%m-%d %H:%M")
                try:
                    return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d %H:%M")
                except:
                    return str(value)
            else:
                return str(value)
        except (TypeError, ValueError):
            return str(value)

    def _render_pagination(self, total_rows: int, options: Dict) -> str:
        """Render pagination controls."""
        page_size = options.get("page_size", 25)
        total_pages = (total_rows + page_size - 1) // page_size
        
        if total_pages <= 1:
            return ""
        
        pages_html = ""
        for i in range(1, total_pages + 1):
            pages_html += f'<button class="page-btn" data-page="{i}">{i}</button>'
        
        return f"""
        <div class="table-pagination">
            <span>Showing {total_rows} rows</span>
            <div class="page-buttons">{pages_html}</div>
        </div>
        """