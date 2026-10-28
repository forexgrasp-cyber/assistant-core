"""
Report Exporters

Export rendered reports to PDF, HTML, CSV, JSON, and other formats.
"""

from __future__ import annotations

import asyncio
import csv
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import RenderedReport, ExportFormat, ExportOptions, WidgetType


class BaseExporter:
    """Base class for exporters."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, report: RenderedReport, extension: str) -> str:
        """Generate unique filename for export."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in report.name if c.isalnum() or c in ("-", "_")).strip()
        return f"{safe_name}_{timestamp}_{uuid.uuid4().hex[:8]}.{extension}"

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size as human-readable string."""
        size = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    async def export(self, report: RenderedReport, output_dir: Path) -> Dict[str, Any]:
        """Export report - implemented by subclasses."""
        raise NotImplementedError


class HTMLExporter(BaseExporter):
    """Export report as standalone HTML file."""

    async def export(self, report: RenderedReport, output_dir: Path) -> Dict[str, Any]:
        filename = self._generate_filename(report, "html")
        filepath = output_dir / filename
        
        html = self._build_html(report)
        
        # Write file
        filepath.write_text(html, encoding="utf-8")
        
        file_size = filepath.stat().st_size
        
        return {
            "format": ExportFormat.HTML.value,
            "filename": filename,
            "path": str(filepath),
            "url": f"/reports/{filename}",
            "size_bytes": file_size,
            "size_human": self._format_size(file_size),
        }

    def _build_html(self, report: RenderedReport) -> str:
        """Build complete HTML document."""
        options = report.export_options
        
        # Collect all widget HTML
        sections_html = ""
        for section in report.sections:
            widgets_html = ""
            for widget in section.widgets:
                if widget.html:
                    widgets_html += f'<div class="widget">{widget.html}</div>'
            
            section_html = f"""
            <section class="report-section" id="{section.section_id}">
                <h2>{section.title}</h2>
                <div class="widgets-grid">
                    {widgets_html}
                </div>
            </section>
            """
            sections_html += section_html
        
        # AI summary if present
        ai_html = ""
        if report.ai_summary:
            ai_html = f"""
            <section class="report-section ai-summary-section">
                <h2>AI Summary</h2>
                <div class="ai-summary">{report.ai_summary}</div>
            </section>
            """
        
        # Build complete HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.name}</title>
    <style>{self._get_styles(options)}</style>
    {self._get_plotly_js() if any(w.chart_config for s in report.sections for w in s.widgets) else ''}
</head>
<body>
    <header class="report-header">
        <div class="header-content">
            <h1>{report.name}</h1>
            <div class="report-meta">
                <span>Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}</span>
                <span>Run ID: {report.run_id}</span>
            </div>
        </div>
    </header>
    
    <main class="report-body">
        {ai_html}
        {sections_html}
    </main>
    
    <footer class="report-footer">
        <p>Report ID: {report.report_id} | Run ID: {report.run_id} | Generated: {report.generated_at.isoformat()}Z</p>
        <p class="confidential">Confidential - For Authorized Recipients Only</p>
    </footer>
    
    <script>{self._get_client_js()}</script>
</body>
</html>"""
        
        return html

    def _get_styles(self, options: ExportOptions) -> str:
        return f"""
        * {{ box-sizing: border-box; }}
        @page {{ size: {options.pdf_page_size} {options.pdf_orientation}; margin: {options.pdf_margins.get('top', '20mm')} {options.pdf_margins.get('right', '15mm')} {options.pdf_margins.get('bottom', '20mm')} {options.pdf_margins.get('left', '15mm')}; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            color: #1f2937;
            line-height: 1.6;
            background: #ffffff;
        }}
        
        .report-header {{
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}
        
        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .report-header h1 {{
            margin: 0 0 12px;
            font-size: 32px;
            font-weight: 700;
            color: #111827;
        }}
        
        .report-meta {{
            display: flex;
            gap: 24px;
            color: #6b7280;
            font-size: 14px;
        }}
        
        .report-body {{
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 40px;
        }}
        
        .report-section {{
            break-inside: avoid;
        }}
        
        .report-section h2 {{
            font-size: 22px;
            font-weight: 600;
            color: #1f2937;
            margin: 0 0 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid #e5e7eb;
        }}
        
        .widgets-grid {{
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 20px;
        }}
        
        .widget {{
            background: #fff;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 20px;
            break-inside: avoid;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        
        .widget h3 {{
            margin: 0 0 16px;
            font-size: 15px;
            font-weight: 600;
            color: #374151;
        }}
        
        .kpi-card {{
            grid-column: span 3;
        }}
        
        .kpi-card.prominent {{
            grid-column: span 6;
        }}
        
        .kpi-card .value {{
            font-size: 36px;
            font-weight: 700;
            color: #111827;
            line-height: 1.2;
        }}
        
        .kpi-card .trend {{
            font-size: 13px;
            font-weight: 500;
            margin-top: 4px;
        }}
        
        .trend.positive {{ color: #059669; }}
        .trend.negative {{ color: #dc2626; }}
        
        .widget.data-table-widget {{
            grid-column: span 12;
        }}
        
        .table-toolbar {{
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }}
        
        .btn-export {{
            padding: 6px 12px;
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
        }}
        
        .btn-export:hover {{ background: #e5e7eb; }}
        
        .table-container {{
            overflow-x: auto;
        }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        
        .data-table th,
        .data-table td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        .data-table th {{
            font-weight: 600;
            color: #374151;
            background: #f9fafb;
            white-space: nowrap;
        }}
        
        .data-table.striped tbody tr:nth-child(even) {{
            background: #f9fafb;
        }}
        
        .data-table.hoverable tbody tr:hover {{
            background: #f3f4f6;
        }}
        
        .data-table td[data-key*="revenue"],
        .data-table td[data-key*="amount"],
        .data-table td[data-key*="value"] {{
            text-align: right;
            font-variant-numeric: tabular-nums;
        }}
        
        .table-pagination {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 0;
            margin-top: 12px;
            border-top: 1px solid #e5e7eb;
        }}
        
        .page-buttons {{
            display: flex;
            gap: 4px;
        }}
        
        .page-btn {{
            padding: 6px 12px;
            border: 1px solid #d1d5db;
            background: white;
            border-radius: 6px;
            cursor: pointer;
        }}
        
        .page-btn.active {{
            background: #3b82f6;
            color: white;
            border-color: #3b82f6;
        }}
        
        .chart-empty {{
            grid-column: span 12;
            text-align: center;
            padding: 40px;
            color: #9ca3af;
        }}
        
        .ai-summary-section .ai-summary {{
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 8px;
            padding: 20px;
            line-height: 1.7;
        }}
        
        .report-footer {{
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #9ca3af;
            font-size: 12px;
        }}
        
        .confidential {{
            font-weight: 600;
            color: #dc2626;
            margin-top: 8px;
        }}
        
        @media print {{
            .widgets-grid {{ grid-template-columns: repeat(6, 1fr); }}
            .widget {{ break-inside: avoid; }}
            .report-header, .report-footer, .table-toolbar {{ display: none; }}
            .kpi-card {{ grid-column: span 3 !important; }}
            .widget.data-table-widget {{ grid-column: span 6 !important; }}
            @page {{ margin: 15mm; }}
        }}
        
        @media (max-width: 768px) {{
            .widgets-grid {{ grid-template-columns: 1fr; }}
            .kpi-card, .kpi-card.prominent {{ grid-column: span 1; }}
            .widget.data-table-widget {{ grid-column: span 1; }}
        }}
        """

    def _get_plotly_js(self) -> str:
        return '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'

    def _get_client_js(self) -> str:
        return """
        // Table sorting
        document.addEventListener('click', function(e) {
            if (e.target.matches('.data-table th[data-key]')) {
                const table = e.target.closest('table');
                const key = e.target.dataset.key;
                const format = e.target.dataset.format;
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                
                const isAsc = !e.target.classList.contains('sort-asc');
                document.querySelectorAll('.data-table th').forEach(th => th.classList.remove('sort-asc', 'sort-desc'));
                e.target.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
                
                rows.sort((a, b) => {
                    const aVal = a.querySelector(`td[data-key="${key}"]`)?.textContent || '';
                    const bVal = b.querySelector(`td[data-key="${key}"]`)?.textContent || '';
                    
                    let cmp = 0;
                    if (format === 'number' || format === 'currency') {
                        cmp = parseFloat(aVal.replace(/[$,]/g, '')) - parseFloat(bVal.replace(/[$,]/g, ''));
                    } else if (format === 'percent') {
                        cmp = parseFloat(aVal.replace('%', '')) - parseFloat(bVal.replace('%', ''));
                    } else if (format === 'date') {
                        cmp = new Date(aVal) - new Date(bVal);
                    } else {
                        cmp = aVal.localeCompare(bVal);
                    }
                    
                    return isAsc ? cmp : -cmp;
                });
                
                rows.forEach(row => tbody.appendChild(row));
            }
        });
        
        // Table export
        document.addEventListener('click', function(e) {
            if (e.target.matches('.btn-export')) {
                const format = e.target.dataset.format;
                const table = e.target.closest('.data-table-widget').querySelector('table');
                exportTable(table, format);
            }
        });
        
        function exportTable(table, format) {
            const rows = Array.from(table.querySelectorAll('tr'));
            const data = rows.map(row => 
                Array.from(row.querySelectorAll('th, td')).map(cell => cell.textContent.trim())
            );
            
            if (format === 'csv') {
                const csv = data.map(row => row.map(cell => '"' + cell.replace(/"/g, '""') + '"').join(',')).join('\\n');
                downloadFile(csv, 'report.csv', 'text/csv');
            } else if (format === 'json') {
                const headers = data[0];
                const jsonData = data.slice(1).map(row => 
                    headers.reduce((obj, h, i) => ({...obj, [h]: row[i]}), {})
                );
                downloadFile(JSON.stringify(jsonData, null, 2), 'report.json', 'application/json');
            }
        }
        
        function downloadFile(content, filename, mimeType) {
            const blob = new Blob([content], {type: mimeType});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        }
        
        // Pagination
        document.addEventListener('click', function(e) {
            if (e.target.matches('.page-btn')) {
                const btn = e.target;
                const page = parseInt(btn.dataset.page);
                const container = btn.closest('.data-table-widget');
                const tbody = container.querySelector('tbody');
                const pageSize = 25;
                
                // Update active state
                container.querySelectorAll('.page-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Show/hide rows
                const rows = Array.from(tbody.querySelectorAll('tr'));
                rows.forEach((row, idx) => {
                    row.style.display = (idx >= (page - 1) * pageSize && idx < page * pageSize) ? '' : 'none';
                });
            }
        });
        """


class PDFExporter(BaseExporter):
    """Export report as PDF using WeasyPrint."""

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)
        self.html_exporter = HTMLExporter(output_dir)

    async def export(self, report: RenderedReport, output_dir: Path) -> Dict[str, Any]:
        filename = self._generate_filename(report, "pdf")
        filepath = output_dir / filename
        
        # Generate HTML first
        html = self.html_exporter._build_html(report)
        
        # Convert to PDF using WeasyPrint
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            font_config = FontConfiguration()
            html_doc = HTML(string=html, base_url=str(output_dir))
            
            # Generate PDF in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: html_doc.write_pdf(
                    str(filepath),
                    font_config=font_config,
                    stylesheets=[
                        CSS(string=f"""
                            @page {{
                                size: {report.export_options.pdf_page_size} {report.export_options.pdf_orientation};
                                margin: {report.export_options.pdf_margins.get('top', '20mm')} 
                                       {report.export_options.pdf_margins.get('right', '15mm')} 
                                       {report.export_options.pdf_margins.get('bottom', '20mm')} 
                                       {report.export_options.pdf_margins.get('left', '15mm')};
                                @bottom-center {{
                                    content: "Page " counter(page) " of " counter(pages);
                                    font-size: 10px;
                                    color: #9ca3af;
                                }}
                            }}
                        """, font_config=font_config)
                    ],
                )
            )
            
        except ImportError:
            # Fallback: use Playwright
            await self._export_with_playwright(html, filepath)
        
        file_size = filepath.stat().st_size
        
        return {
            "format": ExportFormat.PDF.value,
            "filename": filename,
            "path": str(filepath),
            "url": f"/reports/{filename}",
            "size_bytes": file_size,
            "size_human": self._format_size(file_size),
        }

    async def _export_with_playwright(self, html: str, filepath: Path):
        """Fallback PDF generation using Playwright."""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html, wait_until="networkidle")
            await page.pdf(
                path=str(filepath),
                format="A4",
                landscape=False,
                margin={"top": "20mm", "right": "15mm", "bottom": "20mm", "left": "15mm"},
                print_background=True,
            )
            await browser.close()


class CSVExporter(BaseExporter):
    """Export report data as CSV files."""

    async def export(self, report: RenderedReport, output_dir: Path) -> Dict[str, Any]:
        filename = self._generate_filename(report, "zip")
        filepath = output_dir / filename
        
        # Create a ZIP with one CSV per widget that has tabular data
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for section in report.sections:
                for widget in section.widgets:
                    if widget.data and widget.type in (WidgetType.DATA_TABLE, WidgetType.PIVOT_TABLE, WidgetType.SUMMARY_TABLE):
                        csv_filename = f"{section.title}_{widget.title}.csv".replace(" ", "_").replace("/", "_")
                        csv_content = self._data_to_csv(widget.data)
                        zf.writestr(csv_filename, csv_content)
            
            # Also add a combined CSV with all data
            if any(w.data for s in report.sections for w in s.widgets):
                combined_csv = self._combine_all_data(report)
                zf.writestr("all_data_combined.csv", combined_csv)
        
        filepath.write_bytes(zip_buffer.getvalue())
        
        file_size = filepath.stat().st_size
        
        return {
            "format": ExportFormat.CSV.value,
            "filename": filename,
            "path": str(filepath),
            "url": f"/reports/{filename}",
            "size_bytes": file_size,
            "size_human": self._format_size(file_size),
        }

    def _data_to_csv(self, data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def _combine_all_data(self, report: RenderedReport) -> str:
        all_rows = []
        for section in report.sections:
            for widget in section.widgets:
                if widget.data:
                    for row in widget.data:
                        row_copy = row.copy()
                        row_copy["_section"] = section.title
                        row_copy["_widget"] = widget.title
                        all_rows.append(row_copy)
        
        if not all_rows:
            return ""
        
        return self._data_to_csv(all_rows)


class JSONExporter(BaseExporter):
    """Export report as JSON."""

    async def export(self, report: RenderedReport, output_dir: Path) -> Dict[str, Any]:
        filename = self._generate_filename(report, "json")
        filepath = output_dir / filename
        
        # Build serializable report data
        export_data = {
            "report": {
                "id": report.report_id,
                "run_id": report.run_id,
                "name": report.name,
                "generated_at": report.generated_at.isoformat(),
                "total_widgets": report.total_widgets,
                "failed_widgets": report.failed_widgets,
                "total_data_rows": report.total_data_rows,
                "total_render_time_ms": report.total_render_time_ms,
                "ai_summary": report.ai_summary,
            },
            "sections": [],
        }
        
        for section in report.sections:
            section_data = {
                "id": section.section_id,
                "title": section.title,
                "widgets": [],
            }
            
            for widget in section.widgets:
                widget_data = {
                    "id": widget.widget_id,
                    "type": widget.type.value,
                    "title": widget.title,
                    "data_rows": widget.data_rows,
                    "render_time_ms": widget.render_time_ms,
                    "errors": widget.errors,
                    "warnings": widget.warnings,
                }
                
                if widget.data:
                    widget_data["data"] = widget.data
                if widget.chart_config:
                    widget_data["chart_config"] = widget.chart_config
                
                section_data["widgets"].append(widget_data)
            
            export_data["sections"].append(section_data)
        
        # Write JSON
        filepath.write_text(json.dumps(export_data, indent=2, default=str), encoding="utf-8")
        
        file_size = filepath.stat().st_size
        
        return {
            "format": ExportFormat.JSON.value,
            "filename": filename,
            "path": str(filepath),
            "url": f"/reports/{filename}",
            "size_bytes": file_size,
            "size_human": self._format_size(file_size),
        }


class XLSXExporter(BaseExporter):
    """Export report as Excel workbook."""

    async def export(self, report: RenderedReport, output_dir: Path) -> Dict[str, Any]:
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            raise RuntimeError("openpyxl not installed. Install with: pip install openpyxl")
        
        filename = self._generate_filename(report, "xlsx")
        filepath = output_dir / filename
        
        wb = openpyxl.Workbook()
        
        # Styles
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
        header_alignment = Alignment(horizontal="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        
        # Remove default sheet
        wb.remove(wb.active)
        
        # Create one sheet per section
        for section_idx, section in enumerate(report.sections):
            safe_title = "".join(c for c in section.title if c.isalnum() or c in (" ", "-", "_"))[:31]
            ws = wb.create_sheet(title=safe_title or f"Section_{section_idx + 1}")
            
            row_num = 1
            
            for widget_idx, widget in enumerate(section.widgets):
                if not widget.data:
                    continue
                
                # Write widget title
                ws.cell(row=row_num, column=1, value=widget.title).font = Font(bold=True, size=14)
                row_num += 1
                
                # Write headers
                columns = list(widget.data[0].keys()) if widget.data else []
                for col_idx, col in enumerate(columns, 1):
                    cell = ws.cell(row=row_num, column=col_idx, value=col.replace("_", " ").title())
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                    cell.border = thin_border
                row_num += 1
                
                # Write data
                for row_data in widget.data:
                    for col_idx, col in enumerate(columns, 1):
                        cell = ws.cell(row=row_num, column=col_idx, value=row_data.get(col, ""))
                        cell.border = thin_border
                        cell.alignment = Alignment(wrap_text=True)
                        
                        # Apply number formatting
                        val = row_data.get(col)
                        if isinstance(val, (int, float)):
                            if "rate" in col.lower() or "pct" in col.lower():
                                cell.number_format = '0.0%'
                            elif any(kw in col.lower() for kw in ["revenue", "amount", "price", "value", "ltv", "mrr"]):
                                cell.number_format = '$#,##0.00'
                            elif "count" in col.lower() or "total" in col.lower():
                                cell.number_format = '#,##0'
                    row_num += 1
                
                # Auto-fit columns
                for col_idx in range(1, len(columns) + 1):
                    ws.column_dimensions[get_column_letter(col_idx)].width = 18
                
                row_num += 2  # Space between widgets
        
        wb.save(str(filepath))
        
        file_size = filepath.stat().st_size
        
        return {
            "format": ExportFormat.XLSX.value,
            "filename": filename,
            "path": str(filepath),
            "url": f"/reports/{filename}",
            "size_bytes": file_size,
            "size_human": self._format_size(file_size),
        }


class MarkdownExporter(BaseExporter):
    """Export report as Markdown."""

    async def export(self, report: RenderedReport, output_dir: Path) -> Dict[str, Any]:
        filename = self._generate_filename(report, "md")
        filepath = output_dir / filename
        
        lines = [
            f"# {report.name}",
            "",
            f"**Report ID:** {report.report_id}  ",
            f"**Run ID:** {report.run_id}  ",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
            f"**Widgets:** {report.total_widgets}  ",
            f"**Failed:** {report.failed_widgets}  ",
            f"**Data Rows:** {report.total_data_rows}  ",
            "",
            "---",
            "",
        ]
        
        if report.ai_summary:
            lines.extend(["## AI Summary", "", report.ai_summary, "", "---", ""])
        
        for section in report.sections:
            lines.extend([f"## {section.title}", ""])
            
            if section.content:
                lines.extend([section.content, ""])
            
            for widget in section.widgets:
                lines.extend([f"### {widget.title}", ""])
                
                if widget.type in (WidgetType.DATA_TABLE, WidgetType.PIVOT_TABLE, WidgetType.SUMMARY_TABLE) and widget.data:
                    # Table header
                    columns = list(widget.data[0].keys()) if widget.data else []
                    lines.append("| " + " | ".join(c.replace("_", " ").title() for c in columns) + " |")
                    lines.append("| " + " | ".join("---" for _ in columns) + " |")
                    
                    # Table rows
                    for row in widget.data[:100]:  # Limit to 100 rows
                        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
                    
                    if len(widget.data) > 100:
                        lines.append(f"\n*... and {len(widget.data) - 100} more rows*")
                    
                    lines.append("")
                
                elif widget.type in (WidgetType.KPI_CARD, WidgetType.METRIC_CARD) and widget.data:
                    for row in widget.data[:1]:
                        for key, value in row.items():
                            lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
                        lines.append("")
        
        content = "\n".join(lines)
        filepath.write_text(content, encoding="utf-8")
        
        file_size = filepath.stat().st_size
        
        return {
            "format": ExportFormat.MARKDOWN.value,
            "filename": filename,
            "path": str(filepath),
            "url": f"/reports/{filename}",
            "size_bytes": file_size,
            "size_human": self._format_size(file_size),
        }

    def _format_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# Add missing import
import io