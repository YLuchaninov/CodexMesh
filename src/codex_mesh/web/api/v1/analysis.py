"""
Analysis API Router.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from ....api.manager import ProjectManager
from ....contracts.analysis import (
    HotspotAutotuneRequest,
    HotspotAutotuneResponse,
    HotspotsRequest,
    HotspotsResponse,
    RepoMapRequest,
    RepoMapResponse,
    ResolveRequest,
    ResolveResponse,
    SearchRequest,
    SearchResponse,
    SemanticRequest,
    SemanticResponse,
    SymbolInfo,
    SymbolRequest,
    SymbolResponse,
)
from ....contracts.errors import ApiError
from ....services.analysis_service import AnalysisService
from ....services.project_service import ProjectService
from ...dependencies import get_analysis_service, get_project_manager, get_project_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


def ensure_ready(ps: ProjectService) -> None:
    ps.ensure_ready()


@router.post("/search", response_model=SearchResponse)
async def analysis_search(
    req: SearchRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Lexical code search."""
    ensure_ready(ps)
    try:
        out = an.search_code_raw(req.query, limit=req.limit)
        matches = out.get("matches", [])
        if req.path_prefix:
            pref = req.path_prefix.rstrip("/") + "/"
            matches = [m for m in matches if str(m.get("file_path", "")).startswith(pref)]
        return SearchResponse(matches=matches, count=len(matches))
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/semantic", response_model=SemanticResponse)
async def analysis_semantic(
    req: SemanticRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Semantic code search."""
    ensure_ready(ps)
    try:
        out = an.semantic_search_raw(req.query, k=req.limit)
        results = out.get("results") or out.get("matches", [])
        count = out.get("count", len(results))
        return SemanticResponse(results=results, count=count)
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/repomap", response_model=RepoMapResponse)
async def analysis_repomap(
    req: RepoMapRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Generate repository map."""
    ensure_ready(ps)
    try:
        m = an.get_repo_map(req.token_budget)
        return RepoMapResponse(map=m, token_estimate=len(m) / 4)
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/hotspots", response_model=HotspotsResponse)
async def analysis_hotspots(
    req: HotspotsRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Get hotspot analysis."""
    ensure_ready(ps)
    try:
        path = req.path or ""
        rep = an.get_hotspot_raw(path)
        report = rep.get("report", [])[: req.top_n]
        return HotspotsResponse(summary=rep.get("summary", ""), report=report)
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/hotspots/autotune", response_model=HotspotAutotuneResponse)
async def analysis_hotspots_autotune(
    req: HotspotAutotuneRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Auto-calibrate hotspot weights."""
    ensure_ready(ps)
    try:
        result = an.autotune_hotspot_weights(
            target_rate=req.target_rate,
            percentile=req.percentile,
            max_files=req.max_files,
            apply=req.apply,
            path_filter=req.path,
        )
        if "error" in result:
            raise Exception(result["error"])
        return HotspotAutotuneResponse(**result)
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/resolve", response_model=ResolveResponse)
async def analysis_resolve(
    req: ResolveRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Resolve symbol name to node."""
    ensure_ready(ps)
    try:
        result = an.resolve_symbol(req.query, prefer_types=req.prefer_types, limit=req.limit)
        return ResolveResponse(**result)
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/symbol", response_model=SymbolResponse)
async def analysis_symbol(
    req: SymbolRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Get symbol information."""
    ensure_ready(ps)
    try:
        sym = an.get_symbol_info(req.id, include_body=req.include_body)
        if sym.get("error"):
            return SymbolResponse(error=sym.get("error"))
        return SymbolResponse(symbol=SymbolInfo(**sym))
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.get("/docs/coverage")
async def analysis_docs_coverage(
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Get documentation coverage metrics."""
    ensure_ready(ps)
    try:
        result = an.get_doc_coverage_raw()
        return result
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/index-refresh")
async def analysis_index_refresh(
    background_tasks: BackgroundTasks,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
    pm: ProjectManager = Depends(get_project_manager),
):
    """Refresh semantic search index (background task)."""
    ensure_ready(ps)

    def _run_refresh():
        try:
            # Set status to LOADING or just update message
            # We'll keep status as READY but update message/progress to indicate activity
            # because the server is technically still usable for other things.
            # But "LOADING" status might trigger spinners in some UI parts.
            # Let's use a custom message updates.

            pm._update_progress_sync(0, "Starting index refresh...")

            def progress_cb(current, total, msg):
                # Map current/total to percentage (0-100)
                # If total is 0, just show 0 or 100
                pct = 0
                if total > 0:
                    pct = int((current / total) * 100)
                pm._update_progress_sync(pct, f"Indexing: {msg} ({current}/{total})")

            result = an.refresh_index(progress_callback=progress_cb)

            if result.get("success"):
                pm._update_progress_sync(100, "Semantic index refreshed")
            else:
                error_msg = result.get("message") or result.get("error") or "Unknown error"
                pm._update_progress_sync(100, f"Index refresh failed: {error_msg}")

            # Reset message after a short delay or leave it?
            # ProjectManager state is persistent until next change.
            # Let's leave it as "Ready" (which it should be).

        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Background refresh failed: {e}")
            pm._update_progress_sync(100, f"Index refresh failed: {e}")

    background_tasks.add_task(_run_refresh)

    return {"success": True, "message": "Index refresh started in background"}
