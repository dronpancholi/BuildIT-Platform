from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import json
import io
from sqlalchemy import text

from seo_platform.core.database import get_session
from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.services.citation_analytics import citation_analytics
from seo_platform.services.nap_checker import nap_checker
from seo_platform.services.report_generator import report_generator

router = APIRouter()


class GenerateReportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(weekly|monthly|quarterly|custom)$")
    period_start: str
    period_end: str
    report_name: Optional[str] = None
    tenant_id: UUID | None = None


class ReportResponse(BaseModel):
    id: str
    project_id: str
    report_type: str
    report_name: Optional[str]
    period_start: str
    period_end: str
    total_citations_start: int
    total_citations_end: int
    citations_added: int
    nap_consistency_score: int
    avg_domain_authority: int
    generated_at: str


# GET /citations/projects/{id}/analytics
@router.get("/projects/{project_id}/analytics")
async def get_project_analytics(
    project_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Get current analytics summary for a project."""
    try:
        user_id = user.tenant_id
        summary = await citation_analytics.get_project_summary(project_id, user_id)
        breakdown = await citation_analytics.get_status_breakdown(project_id, user_id)
        quality = await citation_analytics.get_quality_metrics(project_id, user_id)
        top_sites = await citation_analytics.get_top_sites(project_id, user_id)

        return {
            "success": True,
            "data": {
                "summary": summary,
                "breakdown": breakdown,
                "quality": quality,
                "top_sites": top_sites
            },
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "ANALYTICS_ERROR", "message": str(e), "details": {}}}


# GET /citations/projects/{id}/analytics/growth
@router.get("/projects/{project_id}/analytics/growth")
async def get_growth_data(
    project_id: UUID,
    days: int = Query(30, ge=7, le=365),
    user: CurrentUser = Depends(get_current_user)
):
    """Get daily citation growth data for charts."""
    try:
        user_id = user.tenant_id
        growth = await citation_analytics.get_growth_data(project_id, user_id, days)

        return {
            "success": True,
            "data": {"growth": growth, "days": days},
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "GROWTH_ERROR", "message": str(e), "details": {}}}


# GET /citations/projects/{id}/analytics/nap
@router.get("/projects/{project_id}/analytics/nap")
async def get_nap_consistency(
    project_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Get NAP consistency report."""
    try:
        user_id = user.tenant_id
        nap = await nap_checker.check_project_nap(project_id, user_id)

        return {
            "success": True,
            "data": nap,
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "NAP_ERROR", "message": str(e), "details": {}}}


# GET /citations/projects/{id}/analytics/competitors
@router.get("/projects/{project_id}/analytics/competitors")
async def get_competitor_comparison(
    project_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Get competitor comparison data."""
    try:
        user_id = user.tenant_id
        competitors = await citation_analytics.get_competitor_comparison(project_id, user_id)

        return {
            "success": True,
            "data": competitors,
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "COMPETITOR_ERROR", "message": str(e), "details": {}}}


# POST /citations/projects/{id}/reports
@router.post("/projects/{project_id}/reports")
async def generate_report(
    project_id: UUID,
    request: GenerateReportRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """Generate and save a report."""
    try:
        user_id = user.tenant_id
        report_data = await report_generator.get_report_data(
            project_id, user_id, request.period_start, request.period_end
        )

        summary = report_data["summary"]

        async with get_session() as session:
            report_id = uuid4()
            await session.execute(text("""
                INSERT INTO citation_reports (
                    id, tenant_id, project_id, report_type, report_name,
                    period_start, period_end,
                    total_citations_start, total_citations_end,
                    citations_added, nap_consistency_score,
                    avg_domain_authority, status_breakdown,
                    competitor_summary, top_sites, report_data,
                    generated_by, generated_at
                ) VALUES (
                    :id, :tid, :pid, :rtype, :rname,
                    :pstart, :pend,
                    :tcs, :tce,
                    :ca, :nap,
                    :ada, :sb,
                    :cs, :ts, :rd,
                    :gb, :ga
                )
            """), {
                "id": str(report_id), "tid": str(user_id), "pid": str(project_id),
                "rtype": request.report_type,
                "rname": request.report_name or f"{request.report_type.title()} Report",
                "pstart": request.period_start, "pend": request.period_end,
                "tcs": 0, "tce": summary["total_citations"],
                "ca": summary["growth_last_30_days"],
                "nap": summary["nap_consistency_score"],
                "ada": summary["avg_domain_authority"],
                "sb": json.dumps(report_data["breakdown"]["statuses"]),
                "cs": json.dumps(report_data["competitors"]),
                "ts": json.dumps(summary["top_sites"][:5]),
                "rd": json.dumps(report_data),
                "gb": str(user_id),
                "ga": datetime.utcnow()
            })
            await session.commit()

        return {
            "success": True,
            "data": {"report_id": str(report_id), "report_data": report_data},
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "REPORT_ERROR", "message": str(e), "details": {}}}


# GET /citations/projects/{id}/reports
@router.get("/projects/{project_id}/reports")
async def list_reports(
    project_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """List saved reports for a project."""
    try:
        user_id = user.tenant_id
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT id, report_type, report_name, period_start, period_end,
                       total_citations_start, total_citations_end,
                       citations_added, nap_consistency_score,
                       avg_domain_authority, generated_at
                FROM citation_reports
                WHERE project_id = :pid AND tenant_id = :tid
                ORDER BY generated_at DESC
            """), {"pid": str(project_id), "tid": str(user_id)})
            rows = result.fetchall()

        reports = [
            ReportResponse(
                id=str(r.id),
                project_id=str(project_id),
                report_type=r.report_type,
                report_name=r.report_name,
                period_start=str(r.period_start),
                period_end=str(r.period_end),
                total_citations_start=r.total_citations_start,
                total_citations_end=r.total_citations_end,
                citations_added=r.citations_added,
                nap_consistency_score=r.nap_consistency_score,
                avg_domain_authority=r.avg_domain_authority,
                generated_at=r.generated_at.isoformat() if r.generated_at else ""
            ).dict()
            for r in rows
        ]

        return {
            "success": True,
            "data": {"reports": reports, "total": len(reports)},
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "LIST_ERROR", "message": str(e), "details": {}}}


# GET /citations/reports/{id}
@router.get("/reports/{report_id}")
async def get_report(
    report_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Get single report details."""
    try:
        user_id = user.tenant_id
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT * FROM citation_reports
                WHERE id = :rid AND tenant_id = :tid
            """), {"rid": str(report_id), "tid": str(user_id)})
            row = result.fetchone()

        if not row:
            return {"success": False, "data": None, "error": {"error_code": "NOT_FOUND", "message": "Report not found", "details": {}}}

        return {
            "success": True,
            "data": {
                "id": str(row.id),
                "project_id": str(row.project_id),
                "report_type": row.report_type,
                "report_name": row.report_name,
                "period_start": str(row.period_start),
                "period_end": str(row.period_end),
                "total_citations_start": row.total_citations_start,
                "total_citations_end": row.total_citations_end,
                "citations_added": row.citations_added,
                "nap_consistency_score": row.nap_consistency_score,
                "avg_domain_authority": row.avg_domain_authority,
                "status_breakdown": json.loads(row.status_breakdown) if row.status_breakdown else {},
                "competitor_summary": json.loads(row.competitor_summary) if row.competitor_summary else {},
                "top_sites": json.loads(row.top_sites) if row.top_sites else [],
                "report_data": json.loads(row.report_data) if row.report_data else {},
                "generated_at": row.generated_at.isoformat() if row.generated_at else ""
            },
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "REPORT_ERROR", "message": str(e), "details": {}}}


# DELETE /citations/reports/{id}
@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Delete a report."""
    try:
        user_id = user.tenant_id
        async with get_session() as session:
            await session.execute(text("""
                DELETE FROM citation_reports WHERE id = :rid AND tenant_id = :tid
            """), {"rid": str(report_id), "tid": str(user_id)})
            await session.commit()

        return {"success": True, "data": {"deleted": True}, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "DELETE_ERROR", "message": str(e), "details": {}}}


# GET /citations/projects/{id}/reports/export
@router.get("/projects/{project_id}/reports/export")
async def export_report(
    project_id: UUID,
    format: str = Query("csv", pattern="^(csv|txt)$"),
    user: CurrentUser = Depends(get_current_user)
):
    """Export submissions as CSV or executive summary as TXT."""
    try:
        user_id = user.tenant_id
        if format == "csv":
            content = await report_generator.generate_csv_export(project_id, user_id)
            filename = f"citations_{project_id}.csv"
            media_type = "text/csv"
        else:
            summary_text = await report_generator.generate_executive_summary(project_id, user_id)
            content = io.BytesIO(summary_text.encode('utf-8'))
            filename = f"summary_{project_id}.txt"
            media_type = "text/plain"

        return StreamingResponse(
            iter([content.getvalue()]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET /citations/projects/{id}/reports/latest
@router.get("/projects/{project_id}/reports/latest")
async def get_latest_report(
    project_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Get latest report for quick access."""
    try:
        user_id = user.tenant_id
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT id, report_type, report_name, period_start, period_end,
                       total_citations_start, total_citations_end,
                       citations_added, nap_consistency_score,
                       avg_domain_authority, report_data, generated_at
                FROM citation_reports
                WHERE project_id = :pid AND tenant_id = :tid
                ORDER BY generated_at DESC
                LIMIT 1
            """), {"pid": str(project_id), "tid": str(user_id)})
            row = result.fetchone()

        if not row:
            return {
                "success": True,
                "data": {"report": None, "message": "No reports generated yet"},
                "error": None
            }

        return {
            "success": True,
            "data": {
                "report": {
                    "id": str(row.id),
                    "report_type": row.report_type,
                    "report_name": row.report_name,
                    "period_start": str(row.period_start),
                    "period_end": str(row.period_end),
                    "total_citations_start": row.total_citations_start,
                    "total_citations_end": row.total_citations_end,
                    "citations_added": row.citations_added,
                    "nap_consistency_score": row.nap_consistency_score,
                    "avg_domain_authority": row.avg_domain_authority,
                    "report_data": json.loads(row.report_data) if row.report_data else {},
                    "generated_at": row.generated_at.isoformat() if row.generated_at else ""
                }
            },
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "LATEST_ERROR", "message": str(e), "details": {}}}


# --- Root-level Reports API support ---

class GenerateRootReportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(weekly|monthly|quarterly|custom)$")
    client_id: UUID
    period_start: Optional[str] = None
    period_end: Optional[str] = None


reports_root_router = APIRouter(prefix="/reports")


@reports_root_router.get("")
async def list_all_reports(
    tenant_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user)
):
    try:
        user_id = user.tenant_id
        tid = tenant_id or user_id
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT id, project_id, report_type, report_name, period_start, period_end,
                       total_citations_start, total_citations_end,
                       citations_added, nap_consistency_score,
                       avg_domain_authority, generated_at
                FROM citation_reports
                WHERE tenant_id = :tid
                ORDER BY generated_at DESC
                LIMIT :limit
            """), {"tid": str(tid), "limit": limit})
            rows = result.fetchall()

        reports = []
        for r in rows:
            reports.append({
                "id": str(r.id),
                "tenant_id": str(tid),
                "client_id": str(tid),
                "project_id": str(r.project_id),
                "title": r.report_name,
                "report_name": r.report_name,
                "report_type": r.report_type,
                "created_at": r.generated_at.isoformat() if r.generated_at else "",
                "updated_at": r.generated_at.isoformat() if r.generated_at else "",
                "data": {
                    "status": "completed",
                    "total_citations_start": r.total_citations_start,
                    "total_citations_end": r.total_citations_end,
                    "citations_added": r.citations_added,
                    "nap_consistency_score": r.nap_consistency_score,
                    "avg_domain_authority": r.avg_domain_authority,
                }
            })
        return {
            "success": True,
            "data": reports,
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "LIST_ERROR", "message": str(e), "details": {}}}


@reports_root_router.post("/generate")
async def generate_root_report(
    request: GenerateRootReportRequest,
    user: CurrentUser = Depends(get_current_user)
):
    try:
        tenant_id = user.tenant_id
        client_id = request.client_id
        
        from seo_platform.models.citation_v2 import CitationProject
        from sqlalchemy import select
        
        async with get_session() as session:
            result = await session.execute(
                select(CitationProject).where(
                    CitationProject.client_id == client_id,
                    CitationProject.tenant_id == tenant_id
                )
            )
            project = result.scalar_one_or_none()
            
            if not project:
                from seo_platform.models.tenant import Client as DBClient
                client_res = await session.execute(
                    select(DBClient).where(
                        DBClient.id == client_id,
                        DBClient.tenant_id == tenant_id
                    )
                )
                db_client = client_res.scalar_one_or_none()
                if not db_client:
                    raise HTTPException(status_code=404, detail="Client not found")
                
                project = CitationProject(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    client_id=client_id,
                    business_name=db_client.name,
                    website_url=f"https://{db_client.domain}" if db_client.domain else "https://example.com",
                    status="active"
                )
                session.add(project)
                await session.commit()
                
            project_id = project.id

        period_start = request.period_start or (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        period_end = request.period_end or datetime.utcnow().strftime("%Y-%m-%d")
        
        report_data = await report_generator.get_report_data(
            project_id, tenant_id, period_start, period_end
        )
        summary = report_data["summary"]

        async with get_session() as session:
            report_id = uuid4()
            await session.execute(text("""
                INSERT INTO citation_reports (
                    id, tenant_id, project_id, report_type, report_name,
                    period_start, period_end,
                    total_citations_start, total_citations_end,
                    citations_added, nap_consistency_score,
                    avg_domain_authority, status_breakdown,
                    competitor_summary, top_sites, report_data,
                    generated_by, generated_at
                ) VALUES (
                    :id, :tid, :pid, :rtype, :rname,
                    :pstart, :pend,
                    :tcs, :tce,
                    :ca, :nap,
                    :ada, :sb,
                    :cs, :ts, :rd,
                    :gb, :ga
                )
            """), {
                "id": str(report_id), "tid": str(tenant_id), "pid": str(project_id),
                "rtype": request.report_type,
                "rname": f"{request.report_type.title()} Report",
                "pstart": period_start, "pend": period_end,
                "tcs": 0, "tce": summary["total_citations"],
                "ca": summary["growth_last_30_days"],
                "nap": summary["nap_consistency_score"],
                "ada": summary["avg_domain_authority"],
                "sb": json.dumps(report_data["breakdown"]["statuses"]),
                "cs": json.dumps(report_data["competitors"]),
                "ts": json.dumps(summary["top_sites"][:5]),
                "rd": json.dumps(report_data),
                "gb": str(tenant_id),
                "ga": datetime.utcnow()
            })
            await session.commit()

        return {
            "success": True,
            "data": {
                "id": str(report_id),
                "tenant_id": str(tenant_id),
                "client_id": str(client_id),
                "title": f"{request.report_type.title()} Report",
                "report_name": f"{request.report_type.title()} Report",
                "report_type": request.report_type,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "data": {
                    "status": "completed",
                    "total_citations_start": 0,
                    "total_citations_end": summary["total_citations"],
                    "citations_added": summary["growth_last_30_days"],
                    "nap_consistency_score": summary["nap_consistency_score"],
                    "avg_domain_authority": summary["avg_domain_authority"],
                }
            },
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "REPORT_ERROR", "message": str(e), "details": {}}}


@reports_root_router.get("/{report_id}")
async def get_root_report(
    report_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    try:
        user_id = user.tenant_id
        async with get_session() as session:
            result = await session.execute(text("""
                SELECT * FROM citation_reports
                WHERE id = :rid AND tenant_id = :tid
            """), {"rid": str(report_id), "tid": str(user_id)})
            row = result.fetchone()

        if not row:
            return {"success": False, "data": None, "error": {"error_code": "NOT_FOUND", "message": "Report not found", "details": {}}}

        client_id = user_id
        try:
            async with get_session() as session:
                project_res = await session.execute(text("""
                    SELECT client_id FROM citation_projects WHERE id = :pid
                """), {"pid": str(row.project_id)})
                p_row = project_res.fetchone()
                if p_row and p_row[0]:
                    client_id = p_row[0]
        except Exception:
            pass

        return {
            "success": True,
            "data": {
                "id": str(row.id),
                "tenant_id": str(row.tenant_id),
                "client_id": str(client_id),
                "project_id": str(row.project_id),
                "title": row.report_name,
                "report_name": row.report_name,
                "report_type": row.report_type,
                "created_at": row.generated_at.isoformat() if row.generated_at else "",
                "updated_at": row.generated_at.isoformat() if row.generated_at else "",
                "data": {
                    "status": "completed",
                    "total_citations_start": row.total_citations_start,
                    "total_citations_end": row.total_citations_end,
                    "citations_added": row.citations_added,
                    "nap_consistency_score": row.nap_consistency_score,
                    "avg_domain_authority": row.avg_domain_authority,
                    "status_breakdown": json.loads(row.status_breakdown) if row.status_breakdown else {},
                    "competitor_summary": json.loads(row.competitor_summary) if row.competitor_summary else {},
                    "top_sites": json.loads(row.top_sites) if row.top_sites else [],
                    "report_data": json.loads(row.report_data) if row.report_data else {},
                }
            },
            "error": None
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"error_code": "REPORT_ERROR", "message": str(e), "details": {}}}


@reports_root_router.delete("/{report_id}")
async def delete_root_report(
    report_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    return await delete_report(report_id, user)

