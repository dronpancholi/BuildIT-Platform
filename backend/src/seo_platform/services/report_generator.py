from io import BytesIO, StringIO
from typing import Dict, Optional
from uuid import UUID
import csv
import json
from datetime import datetime
from sqlalchemy import text

from seo_platform.core.database import get_session
from seo_platform.services.citation_analytics import citation_analytics


class ReportGenerator:
    """
    Generates PDF and CSV reports for citation projects.
    """

    async def generate_csv_export(
        self,
        project_id: UUID,
        tenant_id: UUID
    ) -> BytesIO:
        """Generate CSV export of all submissions."""
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT
                    cs.name as site_name,
                    cs.url as site_url,
                    cs.domain_authority,
                    cs.region,
                    cs.is_premium,
                    s.status,
                    s.submitted_at,
                    s.completed_at,
                    s.form_data,
                    s.status_notes,
                    cs.category
                FROM citation_submissions s
                JOIN citation_sites cs ON s.site_id = cs.id
                WHERE s.project_id = :pid AND s.tenant_id = :tid
                ORDER BY cs.domain_authority DESC NULLS LAST
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            rows = result.fetchall()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Site Name", "URL", "Domain Authority", "Region", "Category",
            "Premium", "Status", "Submitted Date", "Verified Date",
            "Error Message", "Form Data"
        ])

        for row in rows:
            writer.writerow([
                row.site_name or "",
                row.site_url or "",
                row.domain_authority or 0,
                row.region or "",
                row.category or "",
                "Yes" if row.is_premium else "No",
                row.status or "",
                row.submitted_at.strftime("%Y-%m-%d %H:%M") if row.submitted_at else "",
                row.completed_at.strftime("%Y-%m-%d %H:%M") if row.completed_at else "",
                row.status_notes or "",
                json.dumps(row.form_data) if row.form_data else ""
            ])

        output.seek(0)
        return BytesIO(output.getvalue().encode('utf-8'))

    async def generate_executive_summary(
        self,
        project_id: UUID,
        tenant_id: UUID
    ) -> str:
        """Generate text summary for email or quick view."""
        summary = await citation_analytics.get_project_summary(project_id, tenant_id)
        nap = await citation_analytics.calculate_nap_consistency(project_id, tenant_id)
        competitors = await citation_analytics.get_competitor_comparison(project_id, tenant_id)

        lines = [
            "CITATION CAMPAIGN SUMMARY",
            "=" * 50,
            f"Report Date: {datetime.utcnow().strftime('%B %d, %Y')}",
            "",
            "CITATION STATUS",
            "-" * 30,
            f"Total Citations: {summary['total_citations']}",
            f"Live: {summary['live_citations']}",
            f"Pending: {summary['pending_citations']}",
            f"Failed: {summary['failed_citations']}",
            f"Growth (30 days): +{summary['growth_last_30_days']}",
            "",
            "QUALITY METRICS",
            "-" * 30,
            f"Average Domain Authority: {summary['avg_domain_authority']}",
            f"Premium Sites: {summary['total_premium_sites']}",
            f"High DA Sites (>70): {summary['high_da_sites']}",
            f"NAP Consistency: {nap['score']}%",
            "",
        ]

        if competitors["competitors"]:
            lines.extend([
                "COMPETITOR ANALYSIS",
                "-" * 30,
                f"Your Citations: {competitors['client_count']}",
                f"Average Competitor: {competitors['avg_competitor_count']}",
                f"Percentile: {competitors['percentile']}th",
                f"Ahead of {competitors['ahead_of_count']} competitors",
                ""
            ])

        # Top sites
        if summary["top_sites"]:
            lines.extend([
                "TOP PERFORMING SITES",
                "-" * 30
            ])
            for i, site in enumerate(summary["top_sites"][:5], 1):
                lines.append(f"{i}. {site['name']} (DA: {site['da']})")
            lines.append("")

        # NAP issues
        if nap["needs_attention"]:
            lines.extend([
                "NAP ISSUES REQUIRING ATTENTION",
                "-" * 30
            ])
            for issue in nap["needs_attention"][:5]:
                lines.append(f"  [{issue['field'].upper()}] {issue['site']}")
                lines.append(f"    Expected: {issue['expected']}")
                lines.append(f"    Found: {issue['actual']}")
            lines.append("")

        lines.append("=" * 50)
        lines.append("Generated by Citation Automation Platform")

        return "\n".join(lines)

    async def get_report_data(
        self,
        project_id: UUID,
        tenant_id: UUID,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None
    ) -> Dict:
        """Collect all data for a report."""
        summary = await citation_analytics.get_project_summary(project_id, tenant_id)
        nap = await citation_analytics.calculate_nap_consistency(project_id, tenant_id)
        quality = await citation_analytics.get_quality_metrics(project_id, tenant_id)
        competitors = await citation_analytics.get_competitor_comparison(project_id, tenant_id)
        growth = await citation_analytics.get_growth_data(project_id, tenant_id, days=30)
        breakdown = await citation_analytics.get_status_breakdown(project_id, tenant_id)
        top_sites = await citation_analytics.get_top_sites(project_id, tenant_id, limit=10)

        return {
            "project_id": str(project_id),
            "period_start": period_start,
            "period_end": period_end,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": summary,
            "nap": nap,
            "quality": quality,
            "competitors": competitors,
            "growth": growth,
            "breakdown": breakdown,
            "top_sites": top_sites
        }


report_generator = ReportGenerator()
