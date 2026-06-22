from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from collections import defaultdict
import statistics
from sqlalchemy import text

from seo_platform.core.database import get_session


class CitationAnalytics:
    """
    Computes citation analytics and metrics for projects.
    All data comes from real database tables — no mock data.
    """

    def __init__(self):
        self._cache = {}

    async def get_project_summary(
        self,
        project_id: UUID,
        tenant_id: UUID
    ) -> Dict:
        """Get current state summary for a project."""
        async with get_session() as session:
            # Get all submissions
            result = await session.execute(text("""
                SELECT
                    s.status,
                    cs.domain_authority,
                    cs.is_premium,
                    cs.name as site_name,
                    s.submitted_at,
                    s.completed_at
                FROM citation_submissions s
                JOIN citation_sites cs ON s.site_id = cs.id
                WHERE s.project_id = :pid AND s.tenant_id = :tid
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            submissions = result.fetchall()

            # Get project master data
            proj = await session.execute(text("""
                SELECT business_name, phone, email, address,
                       city, state, postal_code, country
                FROM citation_projects
                WHERE id = :pid AND tenant_id = :tid
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            project = proj.fetchone()

            total = len(submissions)
            live = sum(1 for s in submissions if s.status in ("not_started", "in_progress", "pending_review"))
            pending = sum(1 for s in submissions if s.status == "pending")
            failed = sum(1 for s in submissions if s.status in ("failed", "rejected"))
            already_exists = sum(1 for s in submissions if s.status == "already_exists")

            # DA stats
            da_values = [s.domain_authority for s in submissions if s.domain_authority]
            avg_da = int(statistics.mean(da_values)) if da_values else 0
            high_da = sum(1 for s in submissions if s.domain_authority and s.domain_authority > 70)
            premium = sum(1 for s in submissions if s.is_premium)

            # NAP consistency
            nap = await self._calculate_nap_score(session, project, submissions)

            # Growth (last 30 days)
            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).date()
            recent_count = sum(
                1 for s in submissions
                if s.submitted_at and hasattr(s.submitted_at, 'date') and s.submitted_at.date() >= thirty_days_ago
            )

            # Top sites
            top_sites = sorted(
                [{"name": s.site_name, "da": s.domain_authority or 0, "status": s.status}
                 for s in submissions if s.domain_authority],
                key=lambda x: x["da"],
                reverse=True
            )[:10]

            return {
                "total_citations": total,
                "live_citations": live,
                "pending_citations": pending,
                "failed_citations": failed,
                "already_exists_citations": already_exists,
                "avg_domain_authority": avg_da,
                "nap_consistency_score": nap["score"],
                "total_premium_sites": premium,
                "high_da_sites": high_da,
                "top_sites": top_sites,
                "growth_last_30_days": recent_count
            }

    async def get_growth_data(
        self,
        project_id: UUID,
        tenant_id: UUID,
        days: int = 30
    ) -> List[Dict]:
        """Get daily citation counts for growth chart."""
        async with get_session() as session:
            start_date = (datetime.utcnow() - timedelta(days=days)).date()

            # Get all submissions with dates
            result = await session.execute(text("""
                SELECT s.submitted_at, s.status, cs.domain_authority
                FROM citation_submissions s
                JOIN citation_sites cs ON s.site_id = cs.id
                WHERE s.project_id = :pid AND s.tenant_id = :tid
                  AND s.submitted_at IS NOT NULL
                ORDER BY s.submitted_at ASC
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            submissions = result.fetchall()

            # Build daily data
            daily = {}
            for d in range(days + 1):
                current_date = (start_date + timedelta(days=d))
                daily[str(current_date)] = {
                    "date": str(current_date),
                    "total": 0,
                    "live": 0,
                    "pending": 0,
                    "failed": 0
                }

            # Count submissions per day
            for sub in submissions:
                if sub.submitted_at:
                    date_str = sub.submitted_at.strftime("%Y-%m-%d")
                    if date_str in daily:
                        daily[date_str]["total"] += 1
                        if sub.status in ("not_started", "in_progress", "pending_review"):
                            daily[date_str]["live"] += 1
                        elif sub.status == "pending":
                            daily[date_str]["pending"] += 1
                        elif sub.status in ("failed", "rejected"):
                            daily[date_str]["failed"] += 1

            # Calculate running totals
            running_total = 0
            running_live = 0
            running_pending = 0
            running_failed = 0
            for d in range(days + 1):
                date_str = str(start_date + timedelta(days=d))
                daily[date_str]["total"] += running_total
                daily[date_str]["live"] += running_live
                daily[date_str]["pending"] += running_pending
                daily[date_str]["failed"] += running_failed
                running_total = daily[date_str]["total"]
                running_live = daily[date_str]["live"]
                running_pending = daily[date_str]["pending"]
                running_failed = daily[date_str]["failed"]

            return list(daily.values())

    async def get_status_breakdown(
        self,
        project_id: UUID,
        tenant_id: UUID
    ) -> Dict:
        """Get citation status breakdown."""
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT status, COUNT(*) as count
                FROM citation_submissions
                WHERE project_id = :pid AND tenant_id = :tid
                GROUP BY status
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            rows = result.fetchall()

            breakdown = {}
            for row in rows:
                breakdown[row.status] = row.count

            total = sum(breakdown.values())
            percentages = {}
            for status, count in breakdown.items():
                percentages[status] = {
                    "count": count,
                    "percentage": round((count / total * 100) if total else 0, 1)
                }

            return {
                "statuses": breakdown,
                "percentages": percentages,
                "total": total
            }

    async def calculate_nap_consistency(
        self,
        project_id: UUID,
        tenant_id: UUID
    ) -> Dict:
        """Check NAP consistency across all submissions."""
        async with get_session() as session:
            proj = await session.execute(text("""
                SELECT business_name, phone, email, address,
                       city, state, postal_code, country
                FROM citation_projects
                WHERE id = :pid AND tenant_id = :tid
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            project = proj.fetchone()

            result = await session.execute(text("""
                SELECT s.form_data, cs.name as site_name
                FROM citation_submissions s
                JOIN citation_sites cs ON s.site_id = cs.id
                WHERE s.project_id = :pid AND s.tenant_id = :tid
                  AND s.status IN ('live', 'pending')
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            submissions = result.fetchall()

            return await self._calculate_nap_score(session, project, submissions)

    async def _calculate_nap_score(self, session, project, submissions) -> Dict:
        """Internal NAP consistency calculator."""
        if not project or not submissions:
            return {"score": 0, "fields": {}, "total_issues": 0, "needs_attention": []}

        master_name = (project.business_name or "").lower().strip()
        master_phone = self._normalize_phone(project.phone or "")
        master_email = (project.email or "").lower().strip()
        master_address = self._normalize_address(
            f"{project.address or ''} {project.city or ''} {project.state or ''} {project.postal_code or ''}"
        ).strip()

        issues = {"name": [], "phone": [], "email": [], "address": []}
        total_checked = 0

        for sub in submissions:
            form = sub.form_data or {}
            site_name = sub.site_name or "Unknown"
            total_checked += 1

            # Check name
            sub_name = (form.get("business_name", "") or form.get("name", "")).lower().strip()
            if sub_name and self._normalize_name(sub_name) != self._normalize_name(master_name):
                issues["name"].append({
                    "site": site_name,
                    "expected": master_name,
                    "actual": sub_name
                })

            # Check phone
            sub_phone = self._normalize_phone(form.get("phone", ""))
            if sub_phone and sub_phone != master_phone:
                issues["phone"].append({
                    "site": site_name,
                    "expected": master_phone,
                    "actual": sub_phone
                })

            # Check email
            sub_email = (form.get("email", "") or "").lower().strip()
            if sub_email and sub_email != master_email:
                issues["email"].append({
                    "site": site_name,
                    "expected": master_email,
                    "actual": sub_email
                })

            # Check address
            sub_address = self._normalize_address(
                f"{form.get('address', '')} {form.get('city', '')} {form.get('state', '')} {form.get('postal_code', '')}"
            ).strip()
            if sub_address and self._normalize_address(sub_address) != master_address:
                issues["address"].append({
                    "site": site_name,
                    "expected": master_address,
                    "actual": sub_address
                })

        # Calculate scores
        field_scores = {}
        for field, field_issues in issues.items():
            if total_checked > 0:
                consistent = total_checked - len(field_issues)
                field_scores[field] = {
                    "consistent": consistent,
                    "issues": len(field_issues),
                    "score": round((consistent / total_checked) * 100) if total_checked else 0,
                    "details": field_issues
                }

        # Overall score (weighted average)
        scores = [fs["score"] for fs in field_scores.values() if fs["score"] > 0]
        overall_score = int(statistics.mean(scores)) if scores else 100

        # Needs attention items
        needs_attention = []
        for field, field_issues in issues.items():
            for issue in field_issues:
                needs_attention.append({
                    "site": issue["site"],
                    "field": field,
                    "action": "update",
                    "expected": issue["expected"],
                    "actual": issue["actual"]
                })

        return {
            "score": overall_score,
            "fields": field_scores,
            "total_issues": len(needs_attention),
            "needs_attention": needs_attention
        }

    async def get_quality_metrics(
        self,
        project_id: UUID,
        tenant_id: UUID
    ) -> Dict:
        """Calculate quality metrics for a project."""
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT cs.domain_authority, cs.is_premium, cs.name,
                       s.status, cs.importance_score
                FROM citation_submissions s
                JOIN citation_sites cs ON s.site_id = cs.id
                WHERE s.project_id = :pid AND s.tenant_id = :tid
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            submissions = result.fetchall()

            if not submissions:
                return {
                    "avg_domain_authority": 0,
                    "premium_sites_count": 0,
                    "high_da_count": 0,
                    "quality_score": 0,
                    "top_performing_sites": [],
                    "underperforming_sites": []
                }

            da_values = [s.domain_authority for s in submissions if s.domain_authority]
            avg_da = int(statistics.mean(da_values)) if da_values else 0
            premium = sum(1 for s in submissions if s.is_premium)
            high_da = sum(1 for s in submissions if s.domain_authority and s.domain_authority > 70)

            # Quality score composite: DA (40%) + success rate (30%) + premium (30%)
            live_count = sum(1 for s in submissions if s.status in ("not_started", "in_progress", "pending_review"))
            success_rate = (live_count / len(submissions) * 100) if submissions else 0
            da_score = min(avg_da * 1.1, 100)  # Scale DA to 100
            premium_score = min(premium * 3.5, 100)  # Premium sites contribute

            quality_score = int(
                (da_score * 0.4) +
                (success_rate * 0.3) +
                (premium_score * 0.3)
            )

            # Top performing
            top_performing = sorted(
                [{"name": s.name, "da": s.domain_authority or 0, "status": s.status}
                 for s in submissions if s.status == "live" and s.domain_authority],
                key=lambda x: x["da"],
                reverse=True
            )[:5]

            # Underperforming
            underperforming = sorted(
                [{"name": s.name, "da": s.domain_authority or 0, "status": s.status}
                 for s in submissions if s.status in ("failed", "rejected") or (s.domain_authority and s.domain_authority < 30)],
                key=lambda x: x["da"]
            )[:5]

            return {
                "avg_domain_authority": avg_da,
                "premium_sites_count": premium,
                "high_da_count": high_da,
                "quality_score": quality_score,
                "top_performing_sites": top_performing,
                "underperforming_sites": underperforming
            }

    async def get_top_sites(
        self,
        project_id: UUID,
        tenant_id: UUID,
        limit: int = 10
    ) -> List[Dict]:
        """Get top sites by DA that have live citations."""
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT cs.name, cs.domain_authority, cs.is_premium,
                       cs.region, s.status, s.submitted_at
                FROM citation_submissions s
                JOIN citation_sites cs ON s.site_id = cs.id
                WHERE s.project_id = :pid AND s.tenant_id = :tid
                  AND s.status IN ('not_started', 'in_progress', 'pending_review')
                ORDER BY cs.domain_authority DESC NULLS LAST
                LIMIT :lim
            """), {"pid": str(project_id), "tid": str(tenant_id), "lim": limit})
            rows = result.fetchall()

            return [
                {
                    "name": r.name,
                    "domain_authority": r.domain_authority,
                    "is_premium": r.is_premium,
                    "region": r.region,
                    "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None
                }
                for r in rows
            ]

    async def get_competitor_comparison(
        self,
        project_id: UUID,
        tenant_id: UUID
    ) -> Dict:
        """Compare client's citation count vs competitors."""
        async with get_session() as session:
            # Client count
            client_result = await session.execute(text("""
                SELECT COUNT(*) as cnt
                FROM citation_submissions
                WHERE project_id = :pid AND tenant_id = :tid
                  AND status IN ('not_started', 'in_progress', 'pending_review')
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            client_count = client_result.scalar() or 0

            # Competitors
            comp_result = await session.execute(text("""
                SELECT competitor_name, citation_count
                FROM competitor_citations
                WHERE project_id = :pid AND tenant_id = :tid
                ORDER BY citation_count DESC
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            competitors = comp_result.fetchall()

            comp_list = []
            for c in competitors:
                comp_list.append({
                    "name": c.competitor_name,
                    "count": c.citation_count,
                    "ahead": c.citation_count > client_count
                })

            avg_comp = int(statistics.mean([c.citation_count for c in competitors])) if competitors else 0
            ahead_of = sum(1 for c in competitors if client_count > c.citation_count)
            percentile = int((ahead_of / len(competitors) * 100)) if competitors else 100

            return {
                "client_count": client_count,
                "competitors": comp_list,
                "avg_competitor_count": avg_comp,
                "percentile": percentile,
                "ahead_of_count": ahead_of,
                "behind_count": len(competitors) - ahead_of
            }

    # Normalize helpers
    def _normalize_phone(self, phone: str) -> str:
        import re
        if not phone:
            return ""
        digits = re.sub(r'[^\d]', '', phone)
        if digits.startswith('61') and len(digits) > 10:
            digits = digits[2:]
        return digits

    def _normalize_address(self, address: str) -> str:
        if not address:
            return ""
        addr = address.lower().strip()
        replacements = {
            "street": "st", "avenue": "ave", "boulevard": "blvd",
            "drive": "dr", "lane": "ln", "road": "rd",
            "apartment": "apt", "suite": "ste", "unit": "",
            "floor": "fl", "level": "lvl"
        }
        for old, new in replacements.items():
            addr = addr.replace(old, new)
        return addr.strip()

    def _normalize_name(self, name: str) -> str:
        import re
        if not name:
            return ""
        n = name.lower().strip()
        n = re.sub(r'\b(pty ltd|llc|inc|ltd|corp|company|co)\b', '', n)
        n = re.sub(r'[^\w\s]', '', n)
        return n.strip()


citation_analytics = CitationAnalytics()
