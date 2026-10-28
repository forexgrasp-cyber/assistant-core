"""
Email template renderer with MJML support.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional
from uuid import UUID

import mjml
from bs4 import BeautifulSoup
from css_inliner import inline_css

from ..models import EmailTemplate, EmailMessage


class TemplateRenderer:
    """Renders email templates with variable substitution and MJML compilation."""

    def __init__(self):
        self.variable_pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")

    def render_template(
        self,
        template: EmailTemplate,
        variables: Dict[str, Any],
        base_url: str = "",
    ) -> tuple[str, Optional[str]]:
        """
        Render a template with variables.
        Returns (html_content, text_content).
        """
        # Start with MJML if available, otherwise HTML
        if template.mjml_content:
            html = self._render_mjml(template.mjml_content, variables, base_url)
        else:
            html = self._substitute_variables(template.html_content, variables)

        # Inline CSS
        html = self._inline_css(html)

        # Generate text version if not provided
        if template.text_content:
            text = self._substitute_variables(template.text_content, variables)
        else:
            text = self._html_to_text(html)

        return html, text

    def render_message(
        self,
        message: EmailMessage,
        base_url: str = "",
    ) -> tuple[str, Optional[str]]:
        """Render a message with its variables."""
        variables = message.metadata.get("template_variables", {})
        html = self._substitute_variables(message.html_content, variables)
        html = self._inline_css(html)

        if message.text_content:
            text = self._substitute_variables(message.text_content, variables)
        else:
            text = self._html_to_text(html)

        return html, text

    def _render_mjml(self, mjml_content: str, variables: Dict[str, Any], base_url: str) -> str:
        """Compile MJML to HTML with variable substitution."""
        # Substitute variables in MJML first
        mjml_with_vars = self._substitute_variables(mjml_content, variables)
        
        # Add base URL for assets
        if base_url:
            mjml_with_vars = mjml_with_vars.replace(
                'src="',
                f'src="{base_url.rstrip("/")}/'
            ).replace(
                'href="',
                f'href="{base_url.rstrip("/")}/'
            )

        try:
            result = mjml.mjml2html(mjml_with_vars, level="soft")
            if result.get("errors"):
                # Log errors but continue with HTML output
                pass
            return result.get("html", "")
        except Exception:
            # Fallback: return as-is if MJML fails
            return mjml_with_vars

    def _substitute_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """Replace {{variable}} placeholders with values."""
        def replace_var(match):
            var_name = match.group(1)
            value = variables.get(var_name, "")
            if value is None:
                return ""
            return str(value)

        return self.variable_pattern.sub(replace_var, content)

    def _inline_css(self, html: str) -> str:
        """Inline CSS styles into HTML elements."""
        try:
            return inline_css(html)
        except Exception:
            return html

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "head", "meta", "link"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator="\n")

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text

    def validate_template(self, template: EmailTemplate) -> Dict[str, Any]:
        """Validate a template for common issues."""
        issues = []

        # Check for required variables
        html_vars = set(self.variable_pattern.findall(template.html_content))
        text_vars = set(self.variable_pattern.findall(template.text_content or ""))
        all_vars = html_vars | text_vars

        missing_vars = all_vars - set(template.variables)
        if missing_vars:
            issues.append({
                "type": "missing_variables",
                "severity": "warning",
                "message": f"Template uses variables not declared: {', '.join(missing_vars)}",
                "variables": list(missing_vars),
            })

        unused_vars = set(template.variables) - all_vars
        if unused_vars:
            issues.append({
                "type": "unused_variables",
                "severity": "info",
                "message": f"Declared variables not used: {', '.join(unused_vars)}",
                "variables": list(unused_vars),
            })

        # Check subject length
        if len(template.subject) > 998:
            issues.append({
                "type": "subject_too_long",
                "severity": "error",
                "message": f"Subject exceeds 998 characters ({len(template.subject)})",
            })

        # Check for unsubscribe link
        if "{{unsubscribe_url}}" not in template.html_content and "unsubscribe" not in template.html_content.lower():
            issues.append({
                "type": "missing_unsubscribe",
                "severity": "warning",
                "message": "No unsubscribe link found in template",
            })

        # Check for physical address (CAN-SPAM)
        if "address" not in template.html_content.lower() and "{{address}}" not in template.html_content:
            issues.append({
                "type": "missing_address",
                "severity": "warning",
                "message": "No physical address found (required by CAN-SPAM)",
            })

        return {
            "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
        }

    def preview_template(
        self,
        template: EmailTemplate,
        sample_variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a preview of the template with sample data."""
        if sample_variables is None:
            sample_variables = {
                var: f"[{var}]" for var in template.variables
            }
            # Add common defaults
            sample_variables.setdefault("first_name", "John")
            sample_variables.setdefault("last_name", "Doe")
            sample_variables.setdefault("email", "john@example.com")
            sample_variables.setdefault("unsubscribe_url", "https://example.com/unsubscribe")
            sample_variables.setdefault("preferences_url", "https://example.com/preferences")
            sample_variables.setdefault("address", "123 Main St, City, State 12345")

        html, text = self.render_template(template, sample_variables)
        validation = self.validate_template(template)

        return {
            "html": html,
            "text": text,
            "subject": self._substitute_variables(template.subject, sample_variables),
            "preview_text": self._substitute_variables(template.preview_text or "", sample_variables),
            "validation": validation,
        }