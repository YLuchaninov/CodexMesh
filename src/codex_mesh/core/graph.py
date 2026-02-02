"""Code graph builder orchestrating decoupled extractors."""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
from pathlib import Path

import rustworkx as rx

from codex_mesh.extractors.protocols import ExtractorContext, PendingCall, PendingImport
from codex_mesh.extractors.registry import ExtractorRegistry

from .edges import Edge, EdgeType
from .nodes import BaseNode, ClassNode, FileNode, FunctionNode, NodeType
from .protocols import GRAPH_SCHEMA_VERSION
from .shell import safe_shell

logger = logging.getLogger(__name__)


class CodeGraphBuilder:
    """
    Builds a multi-language code dependency graph.

    Extractors are registered via ExtractorRegistry (built-ins + plugins).
    """

    def __init__(self, project_root: str, registry: ExtractorRegistry | None = None):
        self.project_root = Path(project_root).resolve()

        self.registry = registry or ExtractorRegistry.default()

        self.graph: rx.PyDiGraph = rx.PyDiGraph()
        self._node_id_to_index: dict[str, int] = {}
        self._path_to_node_id: dict[str, str] = {}

        self._pending_imports: list[PendingImport] = []
        self._pending_calls: list[PendingCall] = []

    def build(self, exclude_patterns: list[str] | None = None) -> rx.PyDiGraph:
        # Always build from a clean state to avoid stale nodes/edges across rebuilds
        self.graph = rx.PyDiGraph()
        self._node_id_to_index.clear()
        self._path_to_node_id.clear()
        self._pending_imports.clear()
        self._pending_calls.clear()

        exclude_patterns = exclude_patterns or ["**/__pycache__", "**/.git", "**/venv", "**/.venv"]

        files = self._discover_files(exclude_patterns)

        for file_path in files:
            self.process_file(file_path)

        self._resolve_pending_imports()
        self._resolve_pending_calls()
        self._resolve_cross_file_inheritance()
        self._resolve_doc_links()

        return self.graph

    def save_snapshot(self, path: Path | str) -> None:
        path = Path(path)

        nodes_data = [node.model_dump() for node in self.graph.nodes()]

        edges_data = []
        for u_idx in self.graph.node_indices():
            for _, _, edge in self.graph.out_edges(u_idx):
                edges_data.append(edge.model_dump())

        snapshot = {
            "meta": {"version": GRAPH_SCHEMA_VERSION, "root": str(self.project_root)},
            "nodes": nodes_data,
            "edges": edges_data,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

    def load_snapshot(
        self,
        path: Path | str,
        *,
        validate_sources: bool = True,
        exclude_patterns: list[str] | None = None,
    ) -> bool:
        path = Path(path)
        if not path.exists():
            return False

        # Guard against stale snapshots: if source files are newer than the snapshot,
        # refuse to load and force a rebuild. This avoids serving outdated graphs.
        if validate_sources:
            try:
                snapshot_mtime = path.stat().st_mtime
                patterns = exclude_patterns or ["**/__pycache__", "**/.git", "**/venv", "**/.venv"]
                latest_source_mtime = 0.0
                for src in self._discover_files(patterns):
                    try:
                        mtime = src.stat().st_mtime
                        if mtime > latest_source_mtime:
                            latest_source_mtime = mtime
                    except OSError:
                        continue

                # 1s tolerance to avoid FS timestamp granularity edge cases
                if latest_source_mtime > snapshot_mtime + 1.0:
                    return False
            except OSError:
                # If we can't stat snapshot, fall back to current behavior
                pass

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False

        # MVP: keep existing behavior (if you want full restore, add node class dispatch by node_type)
        self.graph = rx.PyDiGraph()
        self._node_id_to_index.clear()
        self._path_to_node_id.clear()

        # Reconstruct Nodes
        for n_data in data.get("nodes", []):
            try:
                # Polymorphic deserialization based on node_type
                n_type = n_data.get("node_type")
                node: BaseNode
                if n_type == NodeType.FILE:
                    node = FileNode(**n_data)
                elif n_type == NodeType.CLASS:
                    node = ClassNode(**n_data)
                elif n_type == NodeType.FUNCTION or n_type == NodeType.METHOD:
                    # FunctionNode covers both
                    node = FunctionNode(**n_data)
                else:
                    node = BaseNode(**n_data)

                self._add_node(node)

            except Exception as e:
                logger.warning("Failed to load node %s: %s", n_data.get("id"), e)

        # Reconstruct Edges
        for e_data in data.get("edges", []):
            try:
                edge = Edge(**e_data)
                self._add_edge(edge)
            except Exception as e:
                logger.warning("Failed to load edge: %s", e)

        return True

    def _discover_files(self, exclude_patterns: list[str]) -> list[Path]:
        import os

        from .ignore import IgnoreMatcher

        ignore = IgnoreMatcher.load(self.project_root, extra_patterns=exclude_patterns)
        supported_exts = self.registry.supported_extensions()

        candidates: list[Path] = []

        # Use os.walk with topdown=True to allow pruning directories
        for dirpath, dirnames, filenames in os.walk(self.project_root, topdown=True):
            base = Path(dirpath)

            # Prune directories: modify dirnames in-place to prevent recursion
            # We must check if the directory ITSELF is ignored relative to root
            dirnames[:] = [d for d in dirnames if not ignore.is_ignored(base / d, is_dir=True)]

            for fn in filenames:
                p = base / fn
                # Fast extension check first
                if p.suffix.lower() not in supported_exts:
                    continue

                # Check if file is ignored
                if ignore.is_ignored(p, is_dir=False):
                    continue

                candidates.append(p)

        # Filter using git check-ignore if inside a git repo (to handle nested .gitignores)
        final_files = []
        if (self.project_root / ".git").exists() and candidates:
            try:
                # Batch check for performance
                stdin_data = "\n".join(
                    str(p.relative_to(self.project_root)) for p in candidates
                ).encode("utf-8")

                res = safe_shell(
                    ["git", "check-ignore", "--stdin"],
                    cwd=str(self.project_root),
                    input=stdin_data,
                    text=False,  # Input is bytes
                )

                ignored_set = set()
                if res.returncode in (0, 1):
                    for line in res.stdout.splitlines():
                        cleaned = line.strip().strip('"')
                        if cleaned:
                            ignored_set.add(cleaned)

                for p in candidates:
                    rel = str(p.relative_to(self.project_root))
                    if rel not in ignored_set:
                        final_files.append(p)
            except Exception as e:
                logger.warning("git check-ignore failed: %s", e)
                final_files = candidates
        else:
            final_files = candidates

        return sorted(final_files)

    def process_file(self, file_path: Path) -> None:
        rel_path = file_path.relative_to(self.project_root).as_posix()

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        try:
            mtime = file_path.stat().st_mtime
        except OSError:
            mtime = 0.0

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        file_node = FileNode.create(
            path=str(file_path), relative_path=rel_path, content_hash=content_hash, mtime=mtime
        )
        self._add_node(file_node)
        self._path_to_node_id[rel_path] = file_node.id

        extractor = self.registry.get_for_path(file_path)
        if not extractor:
            return

        ctx = ExtractorContext(
            project_root=self.project_root, file_path=file_path, relative_path=rel_path
        )
        try:
            result = extractor.extract(ctx, file_node, content)

            for n in result.nodes:
                self._add_node(n)
            for e in result.edges:
                self._add_edge(e)

            self._pending_imports.extend(result.pending_imports)
            self._pending_calls.extend(result.pending_calls)
        except Exception as e:
            logger.exception("Error extracting %s", rel_path)

    def _resolve_pending_imports(self) -> None:
        """
        Resolve pending imports to create IMPORTS edges.

        When imported_names is available (e.g., 'from x import func'), we create
        file→symbol edges. Otherwise, we create file→file edges.
        """
        # Build symbol lookup: (file_path, symbol_name) -> node_id
        file_symbol_lookup: dict[tuple[str, str], str] = {}
        for node in self.graph.nodes():
            if hasattr(node, "file_path") and hasattr(node, "name"):
                file_path = getattr(node, "file_path", "")
                name = getattr(node, "name", "")
                if file_path and name:
                    file_symbol_lookup[(file_path, name)] = node.id

        for imp in self._pending_imports:
            for rel in imp.candidates:
                target_file_id = self._path_to_node_id.get(rel)
                if not target_file_id:
                    continue

                # If we have specific imported names, try to link to those symbols
                if imp.imported_names:
                    for imp_name in imp.imported_names:
                        symbol_id = file_symbol_lookup.get((rel, imp_name))
                        if symbol_id:
                            self._add_edge(
                                Edge.create(
                                    source_id=imp.source_file_id,
                                    target_id=symbol_id,
                                    edge_type=EdgeType.IMPORTS,
                                    metadata={
                                        "raw": imp.raw,
                                        "imported_name": imp_name,
                                        "alias": (imp.alias_map or {}).get(imp_name),
                                    },
                                )
                            )
                        else:
                            # Symbol not found, link to file instead
                            self._add_edge(
                                Edge.create(
                                    source_id=imp.source_file_id,
                                    target_id=target_file_id,
                                    edge_type=EdgeType.IMPORTS,
                                    metadata={
                                        "raw": imp.raw,
                                        "imported_name": imp_name,
                                        "symbol_not_found": True,
                                    },
                                )
                            )
                    break  # Found the file, stop searching candidates

                # Star imports: link to file
                elif imp.is_star:
                    self._add_edge(
                        Edge.create(
                            source_id=imp.source_file_id,
                            target_id=target_file_id,
                            edge_type=EdgeType.IMPORTS,
                            metadata={"raw": imp.raw, "is_star": True},
                        )
                    )
                    break

                # Default: file→file import
                else:
                    # Check for module alias (e.g. import numpy as np)
                    alias = None
                    if imp.alias_map and imp.raw in imp.alias_map:
                        alias = imp.alias_map[imp.raw]

                    self._add_edge(
                        Edge.create(
                            source_id=imp.source_file_id,
                            target_id=target_file_id,
                            edge_type=EdgeType.IMPORTS,
                            metadata={"raw": imp.raw, "module_alias": alias},
                        )
                    )
                    break

    def _resolve_pending_calls(self) -> None:
        """
        Resolve pending call edges with import-aware resolution.

        Resolution priority:
        1. If caller's file imports another file and that file contains the callee -> link
        2. Same file match
        3. Same class (for method calls)
        4. Unique name match
        5. Skip if ambiguous to avoid false positives
        """
        # Build function/method name -> node IDs index
        name_to_ids: dict[str, list[str]] = {}
        id_to_node: dict[str, FunctionNode] = {}
        for node in self.graph.nodes():
            if hasattr(node, "node_type") and getattr(node, "node_type", None) in {
                NodeType.FUNCTION,
                NodeType.METHOD,
            }:
                name = getattr(node, "name", "")
                nid = getattr(node, "id", "")
                if name and nid:
                    name_to_ids.setdefault(name, []).append(nid)
                    id_to_node[nid] = node

        # Build file_id -> contained function IDs
        file_to_functions: dict[str, dict[str, list[str]]] = {}
        for file_id, file_idx in self._node_id_to_index.items():
            file_node = self.graph[file_idx]
            if not isinstance(file_node, FileNode):
                continue
            # Collect functions via CONTAINS edges
            func_by_name: dict[str, list[str]] = {}
            for _, t_idx, edge_data in self.graph.out_edges(file_idx):
                if edge_data.edge_type == EdgeType.CONTAINS:
                    target = self.graph[t_idx]
                    if isinstance(target, FunctionNode):
                        func_by_name.setdefault(target.name, []).append(target.id)
            file_to_functions[file_id] = func_by_name

        for call in self._pending_calls:
            resolved = False

            # 1. Try import-aware resolution
            source_file_node_id = self._path_to_node_id.get(call.file_path)
            if source_file_node_id:
                s_idx = self._node_id_to_index.get(source_file_node_id)
                if s_idx is not None:
                    # Look for outgoing IMPORTS edges
                    for _, t_idx, edge_data in self.graph.out_edges(s_idx):
                        if edge_data.edge_type != EdgeType.IMPORTS:
                            continue

                        target_node = self.graph[t_idx]

                        # Case A: Import points directly to a function/method
                        if (
                            isinstance(target_node, FunctionNode)
                            and target_node.name == call.callee_name
                        ):
                            self._add_edge(
                                Edge.create(call.source_id, target_node.id, EdgeType.CALLS)
                            )
                            resolved = True
                            break

                        # Case B: Import points to a file -> look for function via CONTAINS
                        if isinstance(target_node, FileNode):
                            funcs_in_file = file_to_functions.get(target_node.id, {})
                            candidates = funcs_in_file.get(call.callee_name, [])
                            if len(candidates) == 1:
                                self._add_edge(
                                    Edge.create(call.source_id, candidates[0], EdgeType.CALLS)
                                )
                                resolved = True
                                break
                            elif len(candidates) > 1 and call.receiver:
                                # Try to narrow down by receiver (class name OR module alias)
                                # 1. Check if receiver matches module alias
                                # Find if this target file is imported with an alias matching the receiver
                                alias = edge_data.metadata.get("module_alias")
                                # So we restrict candidates to this file strongly.
                                # If multiple functions match name in this file, it's ambiguous but less likely.
                                # Usually module functions are unique per module.
                                if (
                                    alias
                                    and alias == call.receiver
                                    and call.callee_name in funcs_in_file
                                ):
                                    # Pick the first one (or ensure unique?)
                                    # Python overloads are rare at module level (except dispatch)
                                    target_ids = funcs_in_file[call.callee_name]
                                    if target_ids:
                                        self._add_edge(
                                            Edge.create(
                                                call.source_id, target_ids[0], EdgeType.CALLS
                                            )
                                        )
                                        resolved = True
                                        break

                                # 2. Check class name match (existing logic)
                                narrowed = [
                                    c
                                    for c in candidates
                                    if c in id_to_node and id_to_node[c].class_name == call.receiver
                                ]
                                if len(narrowed) == 1:
                                    self._add_edge(
                                        Edge.create(call.source_id, narrowed[0], EdgeType.CALLS)
                                    )
                                    resolved = True
                                    break

            if resolved:
                continue

            # 2. Fallback to name-based resolution
            ids = name_to_ids.get(call.callee_name)
            if not ids:
                continue
            if len(ids) == 1:
                self._add_edge(Edge.create(call.source_id, ids[0], EdgeType.CALLS))
                continue

            # 3. Prefer same file - use file_path comparison
            same_file = [
                nid
                for nid in ids
                if nid in id_to_node and id_to_node[nid].file_path == call.file_path
            ]
            if len(same_file) == 1:
                self._add_edge(Edge.create(call.source_id, same_file[0], EdgeType.CALLS))
                continue

            # 4. Prefer same class (method call within class)
            caller_node = self.get_node_by_id(call.source_id)
            if caller_node and isinstance(caller_node, FunctionNode) and caller_node.class_name:
                same_class = [
                    nid
                    for nid in ids
                    if nid in id_to_node and id_to_node[nid].class_name == caller_node.class_name
                ]
                if len(same_class) == 1:
                    self._add_edge(Edge.create(call.source_id, same_class[0], EdgeType.CALLS))
                    continue

            # 5. Try receiver-based disambiguation
            if call.receiver:
                receiver_match = [
                    nid
                    for nid in ids
                    if nid in id_to_node and id_to_node[nid].class_name == call.receiver
                ]
                if len(receiver_match) == 1:
                    self._add_edge(Edge.create(call.source_id, receiver_match[0], EdgeType.CALLS))
                    continue

            # Skip if ambiguous to avoid false positives

    def _resolve_cross_file_inheritance(self) -> None:
        """
        Resolve cross-file inheritance by looking up base classes in imported files.

        For each ClassNode with unresolved bases, we:
        1. Check if the file has IMPORTS to other files
        2. Look for matching class names in those imported files
        3. Create INHERITS edges when found
        """
        # Build class name -> class node lookup
        all_classes: dict[str, list[ClassNode]] = {}
        for node in self.graph.nodes():
            if isinstance(node, ClassNode):
                all_classes.setdefault(node.name, []).append(node)

        # Build file -> imported file/symbol edges
        file_imports: dict[str, set[str]] = {}
        for src_idx in self.graph.node_indices():
            src_node = self.graph[src_idx]
            if not isinstance(src_node, FileNode):
                continue
            imported_targets: set[str] = set()
            for _, tgt_idx, edge_data in self.graph.out_edges(src_idx):
                if edge_data.edge_type == EdgeType.IMPORTS:
                    tgt_node = self.graph[tgt_idx]
                    # If imported file, add its classes
                    if isinstance(tgt_node, FileNode):
                        imported_targets.add(tgt_node.relative_path)
                    # If imported class directly, add it
                    elif isinstance(tgt_node, ClassNode):
                        imported_targets.add(tgt_node.file_path)
            file_imports[src_node.relative_path] = imported_targets

        # For each class, try to resolve unresolved bases via imports
        for class_node in self.graph.nodes():
            if not isinstance(class_node, ClassNode):
                continue

            if not class_node.bases:
                continue

            # Get imported files for this class's file
            imported_files = file_imports.get(class_node.file_path, set())

            for base_name in class_node.bases:
                # Normalize base name (handle qualified names like 'module.Class')
                simple_name = base_name.split(".")[-1].split("::")[-1]

                # Check if we already have this inheritance edge
                class_idx = self._node_id_to_index.get(class_node.id)
                if class_idx is None:
                    continue

                already_linked = False
                for _, tgt_idx, edge_data in self.graph.out_edges(class_idx):
                    if edge_data.edge_type == EdgeType.INHERITS:
                        tgt = self.graph[tgt_idx]
                        if isinstance(tgt, ClassNode) and tgt.name == simple_name:
                            already_linked = True
                            break

                if already_linked:
                    continue

                # Look for matching classes in imported files
                candidates = all_classes.get(simple_name, [])
                for candidate in candidates:
                    if candidate.file_path == class_node.file_path:
                        continue  # Already handled by local resolution
                    if candidate.file_path in imported_files:
                        self._add_edge(
                            Edge.create(
                                class_node.id,
                                candidate.id,
                                EdgeType.INHERITS,
                                metadata={"cross_file": True},
                            )
                        )
                        break  # First match wins

    def _resolve_doc_links(self) -> None:
        """Link docs to symbols using DocsLinker."""
        # Late import to avoid circular dependency
        try:
            from ..docs.linker import DocsLinker
        except ImportError:
            return

        # Link
        linker = DocsLinker(self)
        try:
            new_edges = linker.resolve_links()
            for e in new_edges:
                self._add_edge(e)
        except Exception as e:
            logger.warning("Failed to resolve doc links: %s", e)

    def _add_node(self, node: BaseNode) -> int:
        # Upsert: if the node already exists, replace its payload
        # rustworkx implements mapping protocol for nodes: graph[idx] = new_payload
        if node.id in self._node_id_to_index:
            idx = self._node_id_to_index[node.id]
            with contextlib.suppress(Exception):
                self.graph[idx] = node
            return idx
        idx = self.graph.add_node(node)
        self._node_id_to_index[node.id] = idx
        return idx

    def _add_edge(self, edge: Edge) -> None:
        s_idx = self._node_id_to_index.get(edge.source_id)
        t_idx = self._node_id_to_index.get(edge.target_id)
        if s_idx is None or t_idx is None:
            return
        self.graph.add_edge(s_idx, t_idx, edge)

    def get_node_by_id(self, node_id: str) -> BaseNode | None:
        idx = self._node_id_to_index.get(node_id)
        if idx is not None:
            return self.graph[idx]
        return None

    def get_all_nodes(self) -> list[BaseNode]:
        return list(self.graph.nodes())

    def get_nodes_by_type(self, node_type: NodeType) -> list[BaseNode]:
        return [n for n in self.graph.nodes() if getattr(n, "node_type", None) == node_type]

    def get_files(self) -> list[FileNode]:
        return [n for n in self.graph.nodes() if isinstance(n, FileNode)]

    def get_functions(self) -> list[FunctionNode]:
        return [n for n in self.graph.nodes() if isinstance(n, FunctionNode)]

    def get_classes(self) -> list[ClassNode]:
        return [n for n in self.graph.nodes() if isinstance(n, ClassNode)]
