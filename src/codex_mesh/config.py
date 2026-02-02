"""
CodexMesh Configuration System.

Per architecture.md:
- Use declarative JSON/YAML for workflows, plugins, system setup.
- No magic numbers: all thresholds/scores defined in config.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .llm.routing import LLMProfile


@dataclass
class EmbeddingConfig:
    """Embedding engine configuration."""

    engine: str = "fastembed"
    model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 4000
    chunk_overlap: int = 200


@dataclass
class StorageConfig:
    """Storage backend configuration."""

    backend: str = "rustworkx"
    vector_db: str = "lancedb"
    path: str = "./data"


@dataclass
class HotspotConfig:
    """Hotspot scoring weights and thresholds."""

    error_weight: float = 5.0
    warning_weight: float = 1.0
    todo_weight: float = 3.0
    fixme_weight: float = 4.0
    hack_weight: float = 2.0
    # Tension-like metrics
    churn_days: int = 30
    churn_threshold: int = 5  # P0-3 fix: was float 0.5, should be int (min commits)
    churn_commit_weight: float = 0.5

    import_in_weight: float = 0.3
    import_out_weight: float = 0.2
    centrality_weight: float = 0.2  # PageRank centrality weight

    # P2 Multi-Axis Weights
    logic_weight: float = 1.0  # Complexity, nesting
    concurrency_weight: float = 2.0  # Async, locks, threading
    risk_weight: float = 1.5  # External calls, env vars

    # UI/Reporting thresholds
    high_hotspot_threshold: float = 5.0
    analysis_timeout: int = 30


@dataclass
class SearchConfig:
    """Code search configuration defaults."""

    lexical_limit: int = 10
    semantic_k: int = 5
    max_read_chars: int = 10000
    snippet_length: int = 200
    repo_map_token_budget: int = 1024


@dataclass
class ReviewConfig:
    """Reviewer agent defaults."""

    history_limit_quick: int = 10
    history_limit_standard: int = 30
    history_limit_deep: int = 60
    char_limit: int = 30000
    repo_map_budget: int = 1024
    search_k: int = 5


@dataclass
class MCPConfig:
    """MCP server configuration."""

    tools: bool = True
    resources: bool = True
    prompts: bool = True


@dataclass
class DocsConfig:
    """Documentation subsystem configuration."""

    enabled: bool = False
    roots: list[str] = field(default_factory=lambda: ["docs", "."])
    globs: list[str] = field(
        default_factory=lambda: ["README.md", "**/*.md", "**/*.rst", "**/*.adoc"]
    )
    max_section_chars: int = 8000
    stale_days_warn: int = 14
    link_policy: str = "explicit_then_heuristic"  # explicit_only | explicit_then_heuristic
    min_confidence_strict: float = 0.7


@dataclass
class CodexMeshConfig:
    """
    Main configuration for CodexMesh.
    """

    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    hotspot: HotspotConfig = field(default_factory=HotspotConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    review: ReviewConfig = field(default_factory=ReviewConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    docs: DocsConfig = field(default_factory=DocsConfig)
    skills: list[str] = field(default_factory=list)
    workflows_path: str = "./workflows"
    profiles: dict[str, "LLMProfile"] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodexMeshConfig":
        """
        Create a configuration instance from a dictionary.
        """
        config = cls()
        config.update_from_dict(data)
        return config

    def update_from_dict(self, data: dict[str, Any]) -> None:
        """
        Update the current configuration instance from a dictionary (in-place).
        """
        # Late import to avoid circular dependency
        from .llm.routing import LLMProfile

        if "embedding" in data:
            self.embedding = EmbeddingConfig(**data["embedding"])
        if "storage" in data:
            self.storage = StorageConfig(**data["storage"])
        if "hotspot" in data:
            self.hotspot = HotspotConfig(**data["hotspot"])
        if "search" in data:
            self.search = SearchConfig(**data["search"])
        if "review" in data:
            self.review = ReviewConfig(**data["review"])
        if "mcp" in data:
            self.mcp = MCPConfig(**data["mcp"])
        if "docs" in data:
            self.docs = DocsConfig(**data["docs"])
        if "skills" in data:
            self.skills = data["skills"]
        if "workflows_path" in data:
            self.workflows_path = data["workflows_path"]
        if "profiles" in data:
            for name, p_data in data["profiles"].items():
                # Filter to known LLMProfile fields only to avoid TypeError
                # when UI sends unknown fields like 'api_key'
                known_fields = {
                    "name",
                    "model",
                    "provider",
                    "max_tokens",
                    "temperature",
                    "api_key_env",
                    "api_key",
                    "api_base",
                }
                filtered = {k: v for k, v in p_data.items() if k in known_fields}
                self.profiles[name] = LLMProfile(**filtered)

    @classmethod
    def from_file(cls, path: str | Path) -> "CodexMeshConfig":
        """
        Load configuration from a JSON file.

        Args:
            path: Path to the configuration JSON file.

        Returns:
            A populated CodexMeshConfig instance.
        """
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_env(cls) -> "CodexMeshConfig":
        """Create config from environment variables."""
        config = cls()
        config.update_from_env()
        return config

    def update_from_env(self) -> None:
        """Update configuration from environment variables (in-place)."""
        if model := os.environ.get("CODEX_MESH_EMBEDDING_MODEL"):
            self.embedding.model = model
        if path := os.environ.get("CODEX_MESH_STORAGE_PATH"):
            self.storage.path = path

        if os.environ.get("CODEX_MESH_DOCS_ENABLED") == "1":
            self.docs.enabled = True

    def save_to_file(self, path: str | Path) -> None:
        """
        Save the current configuration to a JSON file.
        """
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        # IMPORTANT: do not serialize secrets (api_key) into public config or persisted config.
        profiles_public: dict[str, Any] = {}
        for name, profile in self.profiles.items():
            d = asdict(profile)
            # never expose/persist raw keys
            d.pop("api_key", None)
            profiles_public[name] = d

        return {
            "embedding": {
                "engine": self.embedding.engine,
                "model": self.embedding.model,
                "chunk_size": self.embedding.chunk_size,
                "chunk_overlap": self.embedding.chunk_overlap,
            },
            "storage": {
                "backend": self.storage.backend,
                "vector_db": self.storage.vector_db,
                "path": self.storage.path,
            },
            "hotspot": {
                "error_weight": self.hotspot.error_weight,
                "warning_weight": self.hotspot.warning_weight,
                "todo_weight": self.hotspot.todo_weight,
                "fixme_weight": self.hotspot.fixme_weight,
                "hack_weight": getattr(self.hotspot, "hack_weight", 2.0),
                "churn_days": self.hotspot.churn_days,
                "churn_threshold": self.hotspot.churn_threshold,
                "churn_commit_weight": self.hotspot.churn_commit_weight,
                "import_in_weight": self.hotspot.import_in_weight,
                "import_out_weight": self.hotspot.import_out_weight,
                "centrality_weight": getattr(self.hotspot, "centrality_weight", 0.0),
                "logic_weight": getattr(self.hotspot, "logic_weight", 1.0),
                "concurrency_weight": getattr(self.hotspot, "concurrency_weight", 2.0),
                "risk_weight": getattr(self.hotspot, "risk_weight", 1.5),
                "high_hotspot_threshold": self.hotspot.high_hotspot_threshold,
                "analysis_timeout": self.hotspot.analysis_timeout,
            },
            "search": {
                "lexical_limit": self.search.lexical_limit,
                "semantic_k": self.search.semantic_k,
                "max_read_chars": self.search.max_read_chars,
                "snippet_length": self.search.snippet_length,
                "repo_map_token_budget": self.search.repo_map_token_budget,
            },
            "review": {
                "history_limit_quick": self.review.history_limit_quick,
                "history_limit_standard": self.review.history_limit_standard,
                "history_limit_deep": self.review.history_limit_deep,
                "char_limit": self.review.char_limit,
                "repo_map_budget": self.review.repo_map_budget,
                "search_k": self.review.search_k,
            },
            "mcp": {
                "tools": self.mcp.tools,
                "resources": self.mcp.resources,
                "prompts": self.mcp.prompts,
            },
            "skills": self.skills,
            "workflows_path": self.workflows_path,
            "profiles": profiles_public,
            "docs": {
                "enabled": self.docs.enabled,
                "roots": self.docs.roots,
                "globs": self.docs.globs,
                "max_section_chars": self.docs.max_section_chars,
                "stale_days_warn": self.docs.stale_days_warn,
                "link_policy": self.docs.link_policy,
                "min_confidence_strict": self.docs.min_confidence_strict,
            },
        }
