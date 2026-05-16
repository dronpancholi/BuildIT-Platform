"""
SEO Platform — Reporting Agent
=================================
AI-powered executive report generation with anti-hallucination metric
validation, beautiful HTML rendering, and PDF artifact production via Playwright.
"""

from __future__ import annotations

import base64
import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from seo_platform.core.logging import get_logger
from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReportNarrative(BaseModel):
    """AI-generated narrative sections for a campaign report."""

    executive_summary: str
    keyword_ranking_analysis: str
    backlink_acquisition_analysis: str
    roi_narrative: str
    recommendations: list[str]

    def validate_metrics_grounding(self, kpi_data: dict[str, Any]) -> None:
        """Verify every number cited in the narrative exists in source KPI data.

        Raises ValueError if a hallucinated metric number is detected.
        """
        numbers_in_text: set[str] = set(
            m.group() for m in re.finditer(r"\b\d+(?:\.\d+)?\b", self.executive_summary + " " + self.keyword_ranking_analysis + " " + self.backlink_acquisition_analysis + " " + self.roi_narrative)
        )

        def _collect_values(d: Any, collected: set[str]) -> None:
            if isinstance(d, dict):
                for v in d.values():
                    _collect_values(v, collected)
            elif isinstance(d, list):
                for v in d:
                    _collect_values(v, collected)
            elif isinstance(d, (int, float)):
                collected.add(str(d))

        kpi_numbers: set[str] = set()
        _collect_values(kpi_data, kpi_numbers)

        hallucinated = numbers_in_text - kpi_numbers
        # Common filler numbers like 0, 1, 100, etc. are allowed
        allowed_filler = {"0", "1", "2", "3", "4", "5", "10", "100", "50", "20", "30", "24", "7", "365", "12", "60"}
        hallucinated -= allowed_filler

        if hallucinated:
            raise ValueError(
                f"Hallucinated metric(s) detected: {', '.join(sorted(hallucinated))}. "
                f"These values do not appear in source KPI data."
            )

    @model_validator(mode="after")
    def _check_no_placeholder(self) -> ReportNarrative:
        placeholders = {"N/A", "TBD", "TODO", "PLACEHOLDER", "unknown", "Unknown", "FILL", "XXX"}
        for field_name in self.model_fields:
            val = getattr(self, field_name)
            if isinstance(val, str):
                for p in placeholders:
                    if p in val:
                        raise ValueError(f"Field '{field_name}' contains placeholder text: '{p}'")
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and any(p in item for p in placeholders):
                        raise ValueError(f"Field '{field_name}' contains placeholder text in list item")
        return self


# ---------------------------------------------------------------------------
# Reporting Agent
# ---------------------------------------------------------------------------

class ReportingAgent:
    """Generates AI-powered executive reports with anti-hallucination guards."""

    async def generate_roi_narrative(
        self,
        tenant_id: UUID,
        campaign_id: UUID | None,
        kpi_data: dict[str, Any],
    ) -> ReportNarrative:
        """Generate a grounded ROI narrative from KPI data using the LLM gateway."""
        campaign_section = ""
        if campaign_id:
            campaign_section = f"- Campaign ID: {campaign_id}\n"
        if kpi_data.get("campaigns"):
            for c in kpi_data["campaigns"]:
                campaign_section += (
                    f"  - Campaign: {c.get('name', 'N/A')}\n"
                    f"    Status: {c.get('status', 'N/A')}\n"
                    f"    Target Links: {c.get('target_link_count', 0)}\n"
                    f"    Acquired Links: {c.get('acquired_link_count', 0)}\n"
                    f"    Health Score: {c.get('health_score', 0)}\n"
                )

        summary = kpi_data.get("summary", {})
        metrics_block = (
            f"- Total Campaigns: {summary.get('total_campaigns', 0)}\n"
            f"- Active Campaigns: {summary.get('active_campaigns', 0)}\n"
            f"- Keyword Clusters: {summary.get('total_clusters', 0)}\n"
        )
        if "acquired_links" in summary:
            metrics_block += f"- Acquired Links: {summary['acquired_links']}\n"
        if "total_prospects" in summary:
            metrics_block += f"- Total Prospects: {summary['total_prospects']}\n"
        if "outreach_sent" in summary:
            metrics_block += f"- Outreach Sent: {summary['outreach_sent']}\n"
        if "reply_rate" in summary:
            metrics_block += f"- Reply Rate: {summary['reply_rate']}\n"

        prompt = RenderedPrompt(
            template_id="report_roi_narrative",
            system_prompt=(
                "You are an elite SEO analyst generating executive report narratives. "
                "You MUST ground EVERY metric number you cite in the KPI data provided. "
                "Do NOT invent or extrapolate any metric values. "
                "Return ONLY a JSON object matching the ReportNarrative schema: "
                "{'executive_summary', 'keyword_ranking_analysis', 'backlink_acquisition_analysis', "
                "'roi_narrative', 'recommendations'}."
            ),
            user_prompt=f"""## KPI Data

{metrics_block}

{campaign_section}

Generate a comprehensive executive report narrative covering:
1. Executive summary of overall campaign performance
2. Keyword ranking analysis (focus on clusters and rankings)
3. Backlink acquisition analysis (link building progress)
4. ROI narrative quantifying business impact
5. Strategic recommendations (3-5 items)

IMPORTANT: Every metric number you cite MUST appear in the KPI data above.
DO NOT fabricate or extrapolate values.""",
        )

        result = await llm_gateway.complete(
            task_type=TaskType.ENTERPRISE_REPORTING,
            prompt=prompt,
            output_schema=ReportNarrative,
            tenant_id=tenant_id,
        )

        narrative: ReportNarrative = result.content
        narrative.validate_metrics_grounding(kpi_data)

        return narrative

    async def render_html_report(
        self,
        tenant_id: UUID,
        campaign_id: UUID | None,
        narrative: ReportNarrative,
        kpi_data: dict[str, Any],
    ) -> str:
        """Render a beautiful dark-mode HTML report from narrative and KPI data."""
        summary = kpi_data.get("summary", {})

        def _kpi_card(label: str, value: Any, unit: str = "") -> str:
            return f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}{unit}</div>
            </div>"""

        kpi_cards = "".join([
            _kpi_card("Total Campaigns", summary.get("total_campaigns", 0)),
            _kpi_card("Active Campaigns", summary.get("active_campaigns", 0)),
            _kpi_card("Keyword Clusters", summary.get("total_clusters", 0)),
        ])

        recs_html = "".join(
            f"<li>{rec}</li>" for rec in narrative.recommendations
        ) or "<li>No recommendations available.</li>"

        campaign_rows = ""
        for c in kpi_data.get("campaigns", []):
            campaign_rows += f"""
            <tr>
                <td>{c.get('name', 'N/A')}</td>
                <td><span class="status-badge status-{c.get('status', 'unknown')}">{c.get('status', 'N/A')}</span></td>
                <td>{c.get('acquired_link_count', 0)} / {c.get('target_link_count', 0)}</td>
                <td>{c.get('health_score', 0)}%</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BuildIT Campaign Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e2e8f0;
            line-height: 1.6;
            padding: 40px;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            margin-bottom: 40px;
        }}
        .header h1 {{
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }}
        .header p {{ color: #64748b; font-size: 14px; margin-top: 8px; }}
        .glass-card {{
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 24px;
        }}
        .glass-card h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #c084fc;
            margin-bottom: 16px;
            letter-spacing: -0.3px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        .kpi-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #64748b;
            margin-bottom: 8px;
        }}
        .kpi-value {{
            font-size: 28px;
            font-weight: 700;
            color: #e2e8f0;
        }}
        .narrative-text {{
            color: #cbd5e1;
            font-size: 14px;
            line-height: 1.8;
            white-space: pre-wrap;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            text-align: left;
            padding: 12px 8px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            color: #64748b;
            font-weight: 500;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 12px 8px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            color: #cbd5e1;
        }}
        .status-badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 500;
        }}
        .status-active {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
        .status-completed {{ background: rgba(99,102,241,0.15); color: #6366f1; }}
        .status-paused {{ background: rgba(234,179,8,0.15); color: #eab308; }}
        .status-unknown {{ background: rgba(100,116,139,0.15); color: #64748b; }}
        .recommendations-list {{
            list-style: none;
            padding: 0;
        }}
        .recommendations-list li {{
            position: relative;
            padding: 10px 0 10px 24px;
            color: #cbd5e1;
            font-size: 14px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
        }}
        .recommendations-list li::before {{
            content: "→";
            position: absolute;
            left: 0;
            color: #818cf8;
            font-weight: 600;
        }}
        .footer {{
            text-align: center;
            padding: 24px 0;
            color: #475569;
            font-size: 12px;
            border-top: 1px solid rgba(255,255,255,0.06);
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>BuildIT Campaign Report</h1>
            <p>Enterprise SEO Operational Intelligence</p>
        </div>

        <div class="kpi-grid">
            {kpi_cards}
        </div>

        <div class="glass-card">
            <h2>Executive Summary</h2>
            <div class="narrative-text">{narrative.executive_summary}</div>
        </div>

        <div class="glass-card">
            <h2>Keyword Ranking Analysis</h2>
            <div class="narrative-text">{narrative.keyword_ranking_analysis}</div>
        </div>

        <div class="glass-card">
            <h2>Backlink Acquisition Analysis</h2>
            <div class="narrative-text">{narrative.backlink_acquisition_analysis}</div>
        </div>

        <div class="glass-card">
            <h2>ROI Narrative</h2>
            <div class="narrative-text">{narrative.roi_narrative}</div>
        </div>

        <div class="glass-card">
            <h2>Campaign Details</h2>
            <table>
                <thead>
                    <tr>
                        <th>Campaign</th>
                        <th>Status</th>
                        <th>Links</th>
                        <th>Health</th>
                    </tr>
                </thead>
                <tbody>
                    {campaign_rows if campaign_rows else '<tr><td colspan="4" style="text-align:center;color:#64748b;">No campaign data available.</td></tr>'}
                </tbody>
            </table>
        </div>

        <div class="glass-card">
            <h2>Strategic Recommendations</h2>
            <ul class="recommendations-list">
                {recs_html}
            </ul>
        </div>

        <div class="footer">
            Generated by BuildIT AI — {UUID(tenant_id).hex[:8].upper() if tenant_id else "SYSTEM"}
        </div>
    </div>
</body>
</html>"""

    async def generate_pdf_report(
        self,
        tenant_id: UUID,
        campaign_id: UUID | None,
        html_content: str,
    ) -> bytes:
        """Generate a PDF from HTML content using Playwright headless browser."""
        from playwright.async_api import async_playwright

        logger.info("generating_pdf_report", tenant_id=str(tenant_id)[:8])

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(html_content, wait_until="networkidle")
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"},
            )
            await browser.close()

        return pdf_bytes


reporting_agent = ReportingAgent()
