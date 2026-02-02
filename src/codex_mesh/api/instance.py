"""
CodexMesh Server Instance.

Contains the core logic for a connected project/server instance.
Per architecture.md: No global state - use dependency injection.
"""

import asyncio
import hashlib
import logging
from pathlib import Path

from ..core.context import AppContext
from ..core.graph import CodeGraphBuilder
from ..embeddings.engine import VectorSearch
from ..metrics.hotspot import HotspotCalculator
from ..storage.repomap import RepoMapGenerator
from ..storage.search import GraphSearch

logger = logging.getLogger(__name__)


class CodexMeshServer:
    """
    Main CodexMesh MCP server class.

    Initializes all components and provides code analysis capabilities.
    Per architecture.md: No singletons or mutable globals.
    """

    def __init__(self, project_root: str, context: AppContext):
        """
        Initialize the server with a project root.

        Args:
            project_root: Path to the project to analyze
            context: Application context (config, event bus)
        """
        self.project_root = Path(project_root).resolve()
        self.context = context

        # Validate project root
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {project_root}")

        if not self.project_root.is_dir():
            raise ValueError(f"Project root is not a directory: {project_root}")

        config = self.context.config
        storage_root = Path(config.storage.path).expanduser().resolve()

        # Generate stable project ID based on path
        project_id = hashlib.sha1(str(self.project_root).encode("utf-8")).hexdigest()[:12]
        project_storage = storage_root / "projects" / project_id
        project_storage.mkdir(parents=True, exist_ok=True)
        self.snapshot_path = project_storage / "graph_snapshot.json"

        # Initialize components
        # Initialize components
        from ..extractors.registry import ExtractorRegistry

        reg_default = ExtractorRegistry.default(include_docs=config.docs.enabled)
        self.graph_builder = CodeGraphBuilder(str(self.project_root), registry=reg_default)
        self.hotspot_calc = HotspotCalculator(str(self.project_root), config=self.context.config)
        self.vector_search = VectorSearch(
            db_path=str(project_storage / "lancedb"), config=self.context.config
        )

        # Lazy initialized after graph is built
        self.repomap_gen: RepoMapGenerator | None = None
        self.graph_search: GraphSearch | None = None

        self._initialized = False

    def initialize(self, *, auto_index: bool = True, force_reindex: bool = False) -> None:
        """Build the code graph and initialize all components.

        Args:
            auto_index: Whether to automatically index for semantic search
            force_reindex: Force reindexing even if index exists
        """
        if self._initialized:
            return

        # Try loading snapshot
        loaded = False
        if self.snapshot_path.exists():
            logger.info(f"Loading graph snapshot from {self.snapshot_path}")
            if self.graph_builder.load_snapshot(self.snapshot_path):
                logger.info("Snapshot loaded successfully.")
                loaded = True
            else:
                logger.warning("Snapshot invalid or stale. Rebuilding.")

        if not loaded:
            # Build the code graph
            logger.info(f"Building code graph for: {self.project_root}")
            self.graph_builder.build()

            # Save snapshot
            try:
                logger.debug(f"Saving graph snapshot to {self.snapshot_path}")
                self.graph_builder.save_snapshot(self.snapshot_path)
            except Exception as e:
                logger.warning(f"Failed to save snapshot: {e}")

        # Bind graph to hotspot for coupling metrics
        self.hotspot_calc.bind_graph(self.graph_builder)

        # Initialize dependent components
        self.repomap_gen = RepoMapGenerator(self.graph_builder)
        self.graph_search = GraphSearch(self.graph_builder)

        # Index for vector search based on options
        if auto_index:
            need_index = force_reindex or (not loaded) or (not self.vector_search.has_index())
            if need_index:
                logger.info("Indexing codebase for semantic search...")
                chunk_count = self.vector_search.index_codebase(
                    self.graph_builder,
                    str(self.project_root),
                    # If we rebuilt the graph (snapshot not loaded), ensure index matches.
                    force_reindex=(force_reindex or (not loaded)),
                    progress_callback=None,
                )
                logger.info(f"Indexed {chunk_count} code chunks")
            else:
                logger.info("Using existing semantic index")
        else:
            if force_reindex:
                logger.warning("force_reindex=True ignored because auto_index=False")
            logger.info(
                "Auto-index disabled; semantic search will be unavailable until indexing is enabled."
            )

        # Calculate initial hotspot
        file_paths = [f.relative_path for f in self.graph_builder.get_files()]
        self.hotspot_calc.calculate_all(file_paths)

        self._initialized = True

        # Log stats
        stats = self.get_stats()
        logger.info(f"Graph stats: {stats}")

        # Initialize watcher
        from ..services.watcher_service import WatcherService

        self.watcher = WatcherService(
            self.project_root, self.graph_builder, on_rebuild=self._on_watcher_rebuild
        )

    async def start_watcher(self) -> None:
        """Start the file watcher."""
        if hasattr(self, "watcher") and self.watcher:
            await self.watcher.start()

    async def stop_watcher(self) -> None:
        """Stop the file watcher."""
        if hasattr(self, "watcher") and self.watcher:
            await self.watcher.stop()

    async def _on_watcher_rebuild(self) -> None:
        """Callback invoked after the watcher rebuilds the graph.

        Keeps the snapshot + hotspot metrics in sync.
        (Semantic index reindexing is intentionally not automatic for MVP.)
        """
        try:
            await asyncio.to_thread(self.graph_builder.save_snapshot, self.snapshot_path)
        except Exception:
            logger.warning("Failed to save snapshot after watcher rebuild", exc_info=True)

        try:
            file_paths = [f.relative_path for f in self.graph_builder.get_files()]
            await asyncio.to_thread(self.hotspot_calc.calculate_all, file_paths)
        except Exception:
            logger.warning("Failed to recalculate hotspot after watcher rebuild", exc_info=True)

    async def shutdown(self) -> None:
        """Best-effort cleanup for ProjectManager reconnects / app shutdown."""
        try:
            await self.stop_watcher()
        except Exception:
            logger.warning("Failed to stop watcher during shutdown", exc_info=True)

    def get_stats(self) -> dict:
        """Get statistics about the indexed codebase."""
        return {
            "files": len(self.graph_builder.get_files()),
            "classes": len(self.graph_builder.get_classes()),
            "functions": len(self.graph_builder.get_functions()),
            "total_nodes": self.graph_builder.graph.num_nodes(),
            "total_edges": self.graph_builder.graph.num_edges(),
        }
