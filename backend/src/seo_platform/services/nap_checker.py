import re
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy import text
from seo_platform.core.database import get_session


class NAPChecker:
    """
    Validates Name, Address, Phone, Email consistency
    across citation submissions against project master data.
    """

    def normalize_phone(self, phone: str) -> str:
        """Remove spaces, country codes, normalize format."""
        if not phone:
            return ""
        digits = re.sub(r'[^\d]', '', phone)
        # Australian: strip leading 61
        if digits.startswith('61') and len(digits) > 10:
            digits = digits[2:]
        # US: strip leading 1
        if digits.startswith('1') and len(digits) == 11:
            digits = digits[1:]
        return digits

    def normalize_email(self, email: str) -> str:
        """Lowercase, strip www., ensure @"""
        if not email:
            return ""
        e = email.lower().strip()
        if e.startswith("www."):
            e = e[4:]
        return e

    def normalize_address(self, address: str) -> str:
        """Remove apt/suite/unit numbers, standardize abbreviations"""
        if not address:
            return ""
        addr = address.lower().strip()
        # Remove unit/suite/apt
        addr = re.sub(r'(apt|suite|ste|unit|floor|level|floor)\s*[\d\w]*[,\s]*', '', addr)
        # Standardize abbreviations
        replacements = {
            "street": "st", "avenue": "ave", "boulevard": "blvd",
            "drive": "dr", "lane": "ln", "road": "rd",
            "court": "ct", "place": "pl", "circle": "cir",
            "north": "n", "south": "s", "east": "e", "west": "w"
        }
        for old, new in replacements.items():
            addr = addr.replace(old, new)
        return addr.strip()

    def normalize_name(self, name: str) -> str:
        """Lowercase, remove LLC/PTY/INC, strip punctuation"""
        if not name:
            return ""
        n = name.lower().strip()
        n = re.sub(r'\b(pty ltd|llc|inc|ltd|corp|company|co|proprietary limited)\b', '', n)
        n = re.sub(r'[^\w\s]', '', n)
        return n.strip()

    async def check_project_nap(
        self,
        project_id: UUID,
        tenant_id: UUID
    ) -> Dict:
        """Check all submissions against master NAP."""
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
                  AND s.status IN ('not_started', 'in_progress', 'pending', 'pending_review')
            """), {"pid": str(project_id), "tid": str(tenant_id)})
            submissions = result.fetchall()

        if not project or not submissions:
            return {
                "score": 0,
                "fields": {
                    "name": {"consistent": True, "score": 0, "issues": []},
                    "phone": {"consistent": True, "score": 0, "issues": []},
                    "email": {"consistent": True, "score": 0, "issues": []},
                    "address": {"consistent": True, "score": 0, "issues": []}
                },
                "total_issues": 0,
                "needs_attention": []
            }

        # Master values
        master_name = self.normalize_name(project.business_name or "")
        master_phone = self.normalize_phone(project.phone or "")
        master_email = self.normalize_email(project.email or "")
        master_address = self.normalize_address(
            f"{project.address or ''} {project.city or ''} {project.state or ''} {project.postal_code or ''}"
        )

        # Check each submission
        issues = {"name": [], "phone": [], "email": [], "address": []}
        total_checked = 0

        for sub in submissions:
            form = sub.form_data or {}
            site_name = sub.site_name or "Unknown"
            total_checked += 1

            # Name
            sub_name = self.normalize_name(
                form.get("business_name", "") or form.get("name", "")
            )
            if sub_name and sub_name != master_name:
                issues["name"].append({
                    "site": site_name,
                    "expected": project.business_name or "",
                    "actual": form.get("business_name", "") or form.get("name", "")
                })

            # Phone
            sub_phone = self.normalize_phone(form.get("phone", ""))
            if sub_phone and sub_phone != master_phone:
                issues["phone"].append({
                    "site": site_name,
                    "expected": project.phone or "",
                    "actual": form.get("phone", "")
                })

            # Email
            sub_email = self.normalize_email(form.get("email", ""))
            if sub_email and sub_email != master_email:
                issues["email"].append({
                    "site": site_name,
                    "expected": project.email or "",
                    "actual": form.get("email", "")
                })

            # Address
            sub_address = self.normalize_address(
                f"{form.get('address', '')} {form.get('city', '')} {form.get('state', '')} {form.get('postal_code', '')}"
            )
            if sub_address and sub_address != master_address:
                issues["address"].append({
                    "site": site_name,
                    "expected": f"{project.address or ''} {project.city or ''} {project.state or ''} {project.postal_code or ''}".strip(),
                    "actual": f"{form.get('address', '')} {form.get('city', '')} {form.get('state', '')} {form.get('postal_code', '')}".strip()
                })

        # Calculate field scores
        field_scores = {}
        for field, field_issues in issues.items():
            consistent = total_checked - len(field_issues)
            score = self.calculate_field_score(field_issues, total_checked)
            field_scores[field] = {
                "consistent": len(field_issues) == 0,
                "score": score,
                "issues": field_issues
            }

        overall_score = self.calculate_overall_score(field_scores)

        # Needs attention
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

    def calculate_field_score(self, issues: List, total_submissions: int) -> int:
        """Calculate field consistency score (0-100)."""
        if total_submissions == 0:
            return 100
        consistent = total_submissions - len(issues)
        return round((consistent / total_submissions) * 100)

    def calculate_overall_score(self, field_scores: Dict) -> int:
        """Weighted average of field scores."""
        weights = {"name": 30, "phone": 25, "email": 25, "address": 20}
        total_weight = 0
        weighted_sum = 0
        for field, score_data in field_scores.items():
            weight = weights.get(field, 25)
            weighted_sum += score_data["score"] * weight
            total_weight += weight
        return round(weighted_sum / total_weight) if total_weight else 0


nap_checker = NAPChecker()
