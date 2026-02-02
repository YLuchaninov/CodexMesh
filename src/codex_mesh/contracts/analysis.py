"""
Analysis contracts.

Models for code analysis operations: search, semantic, repomap, hotspots, symbols.
"""

from typing import Any

from pydantic import BaseModel, Field

# --- Search ---


class SearchRequest(BaseModel):
    """Lexical code search request."""

    query: str = Field(..., description="Search query")
    path_prefix: str | None = Field(None, description="Filter by path prefix")
    limit: int = Field(50, ge=1, le=500)


class SearchMatch(BaseModel):
    """A single search match."""

    id: str = Field(..., description="Unique node ID")
    node_id: str | None = Field(None, description="Alias for id")
    name: str | None = None
    type: str | None = None
    file_path: str
    line: int | None = Field(None, alias="line_start")
    line_start: int | None = None
    line_end: int | None = None
    span: dict[str, int] | None = None
    snippet: str = ""
    score: float | None = None

    model_config = {"populate_by_name": True}


class SearchResponse(BaseModel):
    """Lexical search response."""

    matches: list[SearchMatch] = Field(default_factory=list)
    count: int = 0


# --- Semantic Search ---


class SemanticRequest(BaseModel):
    """Semantic search request."""

    query: str = Field(..., description="Natural language query")
    limit: int = Field(20, ge=1, le=200)


class SemanticResult(BaseModel):
    """A semantic search result."""

    id: str = Field(..., description="Unique node ID")
    node_id: str | None = Field(None, description="Alias for id")
    name: str
    file_path: str | None = None
    score: float
    snippet: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    span: dict[str, int] | None = None

    model_config = {"populate_by_name": True}


class SemanticResponse(BaseModel):
    """Semantic search response."""

    results: list[SemanticResult] = Field(default_factory=list)
    count: int = 0


# --- RepoMap ---


class RepoMapRequest(BaseModel):
    """RepoMap generation request."""

    token_budget: int = Field(1600, ge=200, le=10000)


class RepoMapResponse(BaseModel):
    """RepoMap response."""

    map: str = Field(..., description="Repository map markdown")
    token_estimate: float = Field(0, description="Estimated token count")


# --- Hotspots ---


class HotspotsRequest(BaseModel):
    """Hotspots analysis request."""

    path: str | None = Field(None, description="Optional file path filter")
    top_n: int = Field(25, ge=1, le=200)


class HotspotItem(BaseModel):
    """A single hotspot item."""

    file_path: str | None = None
    id: str | None = Field(None, alias="node_id")
    hotspot_score: float = Field(0, alias="total")
    structural: float = 0
    semantic: float = 0
    churn: float | None = None
    coupling: float | None = None
    issues: list[dict[str, Any]] = Field(default_factory=list)
    notes: str | None = None

    model_config = {"populate_by_name": True}


class HotspotsResponse(BaseModel):
    """Hotspots analysis response."""

    summary: str = ""
    report: list[HotspotItem] = Field(default_factory=list)


# --- Symbol Resolution ---


class ResolveRequest(BaseModel):
    """Symbol resolution request."""

    query: str = Field(..., description="Symbol name or query")
    prefer_types: list[str] | None = Field(None, description="Types to prioritize")
    limit: int = Field(5, ge=1, le=50)


class ResolvedSymbol(BaseModel):
    """A resolved symbol candidate."""

    id: str = Field(..., description="Unique node ID")
    node_id: str | None = Field(None, description="Alias for id")
    name: str
    type: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    span: dict[str, int] | None = None
    qualified_name: str | None = None
    score: float | None = None

    model_config = {"populate_by_name": True}


class ResolveResponse(BaseModel):
    """Symbol resolution response."""

    best: ResolvedSymbol | None = None
    candidates: list[ResolvedSymbol] = Field(default_factory=list)
    count: int = 0
    confidence: float = 0.0


# --- Symbol Info ---


class SymbolRequest(BaseModel):
    """Symbol info request."""

    id: str = Field(..., description="Node ID")
    include_body: bool = Field(False, description="Include source code body")


class SymbolInfo(BaseModel):
    """Detailed symbol information."""

    id: str = Field(..., description="Unique node ID")
    node_id: str | None = Field(None, description="Alias for id")
    name: str
    type: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    span: dict[str, int] | None = None
    body: str | None = None
    qualified_name: str | None = None
    summary_md: str | None = None
    found: bool = True
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class SymbolResponse(BaseModel):
    """Symbol info response."""

    symbol: SymbolInfo | None = None
    error: str | None = None


# --- Hotspot Autotune ---


class HotspotAutotuneRequest(BaseModel):
    """Request for hotspot weight auto-calibration."""

    path: str | None = Field(None, description="Optional path filter for files to analyze")
    apply: bool = Field(False, description="Apply recommended weights to config")
    target_rate: float = Field(
        0.05, ge=0.01, le=0.5, description="Target hotspot rate (e.g., 0.05 = top 5%)"
    )
    percentile: int = Field(95, ge=50, le=99, description="Percentile for threshold calculation")
    max_files: int = Field(800, ge=10, le=5000, description="Max files to analyze")


class HotspotAutotuneResponse(BaseModel):
    """Response from hotspot weight auto-calibration."""

    recommended: dict[str, Any] = Field(default_factory=dict)
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    applied: bool = False
