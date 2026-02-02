"""Vector-based semantic search using LanceDB and FastEmbed."""

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import lancedb  # type: ignore
from lancedb.pydantic import LanceModel, Vector  # type: ignore

from ..core.graph import CodeGraphBuilder
from ..core.nodes import ClassNode, FileNode, FunctionNode

if TYPE_CHECKING:
    pass

# Set cache path for FastEmbed models
os.environ.setdefault("FASTEMBED_CACHE_PATH", str(Path.home() / ".cache" / "fastembed"))


@dataclass
class SearchResult:
    """Result of a semantic search."""

    node_id: str
    name: str
    file_path: str
    content: str
    score: float
    line_start: int
    line_end: int


class CodeChunk(LanceModel):
    """Schema for code chunks in LanceDB."""

    node_id: str
    name: str
    file_path: str
    content: str
    line_start: int
    line_end: int
    node_type: str
    vector: Vector(384)  # type: ignore  # bge-small-en-v1.5 produces 384-dim vectors


class VectorSearch:
    """
    Semantic code search using embeddings.

    Uses LanceDB for vector storage and FastEmbed for embedding generation.
    Per architecture.md: Model name loaded from config via DI.
    """

    TABLE_NAME = "code_chunks"

    def __init__(self, db_path: str, config: Any):
        """
        Initialize vector search.

        Args:
            db_path: Path for LanceDB storage
            config: CodexMesh configuration
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        self.config = config
        # Load model name from config
        self._model_name = config.embedding.model

        # MVP Guard: Vector dimension is hardcoded to 384 currently
        # If user switches to a different model in config, we must warn/fail
        if self._model_name != "BAAI/bge-small-en-v1.5":
            raise ValueError(
                f"Unsupported embedding model: {self._model_name}. "
                "MVP release only supports 'BAAI/bge-small-en-v1.5' (384 dim)."
            )

        self._db = lancedb.connect(str(self.db_path))
        self._table = None
        self._embedder = None
        self._load_error: str | None = None

    def _get_embedder(self):
        """Lazy load the embedding model."""
        if self._embedder is None and self._load_error is None:
            try:
                from fastembed import TextEmbedding

                self._embedder = TextEmbedding(model_name=self._model_name)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                self._load_error = str(e)  # Store error for later reporting
                logger.warning(f"Failed to load embedding model '{self._model_name}': {e}")
                self._embedder = None
        return self._embedder

    def has_index(self) -> bool:
        """Check if the semantic index table exists."""
        return self.TABLE_NAME in self._db.table_names()

    def _index_meta_path(self) -> Path:
        """Get path for index metadata file (stored alongside lancedb)."""
        # db_path = .../projects/<id>/lancedb → meta is at .../projects/<id>/index_meta.json
        return self.db_path.parent / "index_meta.json"

    def write_index_meta(
        self,
        *,
        project_root: str,
        graph_builder: "CodeGraphBuilder",
        chunks_indexed: int,
    ) -> None:
        """Write index metadata for freshness tracking."""
        logger = logging.getLogger(__name__)
        try:
            now = datetime.now(UTC)
            meta = {
                "schema_version": 1,
                "updated_at": now.isoformat(),
                "updated_at_ts": now.timestamp(),
                "project_root": str(Path(project_root).resolve()),
                "embedding_model": self._model_name,
                "vector_db": "lancedb",
                "db_path": str(self.db_path),
                "table": self.TABLE_NAME,
                "chunks_indexed": int(chunks_indexed),
                "graph": {
                    "nodes": int(graph_builder.graph.num_nodes()),
                    "edges": int(graph_builder.graph.num_edges()),
                },
            }
            self._index_meta_path().write_text(json.dumps(meta, indent=2), encoding="utf-8")
            logger.debug(f"Wrote index_meta.json: {chunks_indexed} chunks indexed")
        except Exception as e:
            # Don't fail indexing due to meta write failure
            logger.warning(f"Failed to write index_meta.json: {e}")

    def read_index_meta(self) -> dict[str, Any] | None:
        """Read index metadata if it exists."""
        p = self._index_meta_path()
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to read index_meta.json: {e}")
            return None

    def index_codebase(
        self,
        graph_builder: CodeGraphBuilder,
        project_root: str,
        force_reindex: bool = False,
        progress_callback: Any = None,  # Callable[[int, int, str], None]
    ) -> int:
        """
        Index all code chunks from the graph.

        Args:
            graph_builder: Built code graph
            project_root: Root path of the project
            force_reindex: If True, drop and rebuild index even if it exists.
                          If False (default), skip indexing if table already exists.
            progress_callback: Optional callback(current, total, message)

        Returns:
            Number of chunks indexed (0 if skipped)
        """
        # Skip if index exists and not forcing reindex
        if self.has_index() and not force_reindex:
            return 0

        project_path = Path(project_root)
        chunks = []

        if progress_callback:
            progress_callback(0, 0, "Extracting code chunks...")

        # Extract functions and classes for indexing
        for node in graph_builder.graph.nodes():
            if isinstance(node, FunctionNode):
                content = self._get_function_content(node, project_path)
                if content:
                    chunks.append(
                        {
                            "node_id": node.id,
                            "name": node.name,
                            "file_path": node.file_path,
                            "content": content,
                            "line_start": node.line_start,
                            "line_end": node.line_end,
                            "node_type": "function",
                        }
                    )

            elif isinstance(node, ClassNode):
                content = self._get_class_summary(node, project_path)
                if content:
                    chunks.append(
                        {
                            "node_id": node.id,
                            "name": node.name,
                            "file_path": node.file_path,
                            "content": content,
                            "line_start": node.line_start,
                            "line_end": node.line_end,  # P0-2 fix: was missing
                            "node_type": "class",
                        }
                    )

            elif hasattr(node, "node_type") and node.node_type.value == "doc_section":
                # Index DocSectionNode
                # Assuming node is DocSectionNode. We import it locally or use attribute check.
                content = f"# {getattr(node, 'title', '')}\n{getattr(node, 'content', '')}"
                # Limit size
                if len(content) > self.config.embedding.chunk_size:
                    content = content[: self.config.embedding.chunk_size] + "\n# ... (truncated)"

                chunks.append(
                    {
                        "node_id": node.id,
                        "name": getattr(node, "title", "Doc"),
                        "file_path": getattr(node, "file_path", ""),
                        "content": content,
                        "line_start": getattr(node, "line_start", 0),
                        "line_end": getattr(node, "line_end", 0),
                        "node_type": "doc_section",
                    }
                )

            elif isinstance(node, FileNode):
                # Index FileNode overview
                content = self._get_file_overview(node, project_path, graph_builder)
                if content:
                    chunks.append(
                        {
                            "node_id": node.id,
                            "name": node.name,
                            "file_path": node.relative_path,
                            "content": content,
                            "line_start": 0,
                            "line_end": 0,  # File overview concept
                            "node_type": "file",
                        }
                    )

        if not chunks:
            return 0

        # Generate embeddings
        embedder = self._get_embedder()

        # Check if embedder creation failed previously
        if self._load_error:
            raise RuntimeError(f"Embedding model unavailable: {self._load_error}")

        if not embedder:
            # Should be covered by _load_error check, but safe fallback
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("Skipping indexing: Embedding model unavailable.")
            raise RuntimeError("Embedding model unavailable (unknown error)")

        contents = [c["content"] for c in chunks]
        embeddings = []

        total_chunks = len(contents)
        if progress_callback:
            progress_callback(
                0, total_chunks, f"Generating embeddings for {total_chunks} chunks..."
            )

        # Batch processing for progress reporting
        # FastEmbed returns a generator, so we iterate
        embedding_generator = embedder.embed(contents)

        # We can't know exact batch size easily from here without peeking implementation,
        # but typically it yields one vector at a time or in batches.
        # FastEmbed.embed returns generator of vectors.
        # Wait, fastembed.TextEmbedding.embed returns Iterable[np.ndarray], one per document?
        # Or batches? Documentation says "Returns a list of embeddings".
        # Actually it returns a generator. Let's iterate and count.

        for i, embedding in enumerate(embedding_generator):
            embeddings.append(embedding)
            if progress_callback and i % 50 == 0:
                progress_callback(
                    i + 1, total_chunks, f"Generated {i + 1}/{total_chunks} embeddings..."
                )

        if progress_callback:
            progress_callback(total_chunks, total_chunks, "Saving to vector database...")

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            chunk["vector"] = (
                embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
            )

        # Drop existing table if it exists (force_reindex or first time)
        if self.TABLE_NAME in self._db.table_names():
            self._db.drop_table(self.TABLE_NAME)

        self._table = self._db.create_table(self.TABLE_NAME, chunks)

        # Write index meta for stale detection
        self.write_index_meta(
            project_root=project_root,
            graph_builder=graph_builder,
            chunks_indexed=len(chunks),
        )

        return len(chunks)

    def search(
        self,
        query: str,
        k: int | None = None,
        filter_type: str | None = None,
        filter_types: list[str] | None = None,
    ) -> list[SearchResult]:
        """
        Search for code chunks semantically similar to the query.

        Args:
            query: Natural language query
            k: Number of results to return
            filter_type: Optional filter by node type ("function" or "class")

        Returns:
            List of search results with scores
        """
        if k is None:
            k = self.config.search.semantic_k
        if self._table is None:
            if self.TABLE_NAME in self._db.table_names():
                self._table = self._db.open_table(self.TABLE_NAME)
            else:
                return []

        # Generate query embedding
        embedder = self._get_embedder()
        if not embedder:
            return []

        query_embeddings = list(embedder.embed([query]))
        query_embedding = query_embeddings[0]

        # Build search query
        # Ensure it's a list for LanceDB search if it's not already
        search_vec = (
            query_embedding.tolist()
            if hasattr(query_embedding, "tolist")
            else list(query_embedding)
        )
        if self._table is None:
            return []

        search_query = self._table.search(search_vec).limit(k)

        if filter_types:
            # LanceDB SQL filter
            types_str = ", ".join(f"'{t}'" for t in filter_types)
            search_query = search_query.where(f"node_type IN ({types_str})")
        elif filter_type:
            search_query = search_query.where(f"node_type = '{filter_type}'")

        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"VectorSearch: executing query '{query}'")

        try:
            results = search_query.to_list()
            logger.debug(f"VectorSearch: found {len(results)} raw matches")
        except Exception as e:
            logger.error(f"VectorSearch: query execution failed: {e}", exc_info=True)
            return []

        return [
            SearchResult(
                node_id=r["node_id"],
                name=r["name"],
                file_path=r["file_path"],
                content=r["content"],
                # P0-4 fix: normalize distance to [0,1] similarity
                score=1.0 / (1.0 + float(r.get("_distance", 0.0) or 0.0)),
                line_start=r["line_start"],
                line_end=r["line_end"],
            )
            for r in results
        ]

    def _get_function_content(self, node: FunctionNode, project_root: Path) -> str | None:
        """Extract function content from file."""
        file_path = project_root / node.file_path
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            # Extract function lines (with some buffer)
            start = max(0, node.line_start - 1)
            end = min(len(lines), node.line_end)
            content = "\n".join(lines[start:end])

            # Prepend docstring context if available
            if node.docstring:
                content = f"# {node.docstring}\n{content}"

            # Limit content size
            # Limit content size
            # User feedback: Don't cut by //2, use full chunk size or rely on smart truncation.
            # We'll use the full chunk size limit (assuming config.chunk_size is chars ~ tokens*4)
            if len(content) > self.config.embedding.chunk_size:
                content = content[: self.config.embedding.chunk_size] + "\n# ... (truncated)"

            return content
        except (OSError, UnicodeDecodeError):
            return None

    def _get_class_summary(self, node: ClassNode, project_root: Path) -> str | None:
        """Extract class summary for indexing."""
        parts = [f"class {node.name}"]

        if node.bases:
            parts[0] += f"({', '.join(node.bases)})"

        if node.docstring:
            parts.append(f'"""{node.docstring}"""')

        return "\n".join(parts)

    def _get_file_overview(
        self, node: FileNode, project_root: Path, graph_builder: CodeGraphBuilder
    ) -> str | None:
        """
        Extract file overview context.
        Includes module docstring, imports, and top-level definitions summary.
        """
        file_path = project_root / node.relative_path
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        lines = content.splitlines()
        overview_parts = []

        # 1. Module Docstring / Imports / Header
        # Improved heuristic: Take more context (up to 150 lines or 4000 chars)
        # to capture imports and module-level docs better.
        head_lines = []
        char_count = 0
        MAX_HEAD_CHARS = 4000

        for line in lines:
            if char_count + len(line) > MAX_HEAD_CHARS:
                break
            head_lines.append(line)
            char_count += len(line)
            if len(head_lines) >= 150:
                break

        overview_parts.append("\n".join(head_lines))

        # 2. Outline of definitions in this file
        # Find all functions/classes in this file from graph
        definitions = []
        for n in graph_builder.graph.nodes():
            fp = getattr(n, "file_path", None)
            # Check relative path match
            if fp == node.relative_path:
                if isinstance(n, ClassNode):
                    definitions.append(f"class {n.name}")
                elif isinstance(n, FunctionNode):
                    sig = getattr(n, "signature", None) or f"def {n.name}(...)"
                    definitions.append(sig)

        if definitions:
            overview_parts.append("\n# Definitions in this file:")
            overview_parts.extend(
                f"# - {d}" for d in definitions[:50]
            )  # Limit to top 50 to avoid token explosion
            if len(definitions) > 50:
                overview_parts.append(f"# ... and {len(definitions) - 50} more")

        return "\n".join(overview_parts)
