"""Hotspot score calculator for code quality analysis."""

import contextlib
import io
import json
import re
import subprocess
import tokenize
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..core.shell import safe_shell

# Using regex for multi-language TODO detection per instructions
# This avoids dependency on 12+ tree-sitter grammars just for comment parsing.

if TYPE_CHECKING:
    pass


@dataclass
class HotspotScore:
    """Hotspot score for a code element."""

    node_id: str
    file_path: str | None = None
    structural: float = 0.0
    behavioral: float = 0.0
    semantic: float = 0.0
    graph: float = 0.0  # Coupling/Centrality
    complexity: float = 0.0  # P2: Logic + Concurrency
    risk: float = 0.0  # P2: Integrations + Ops
    issues: list[dict] = field(default_factory=list)

    @property
    def total(self) -> float:
        """Total hotspot score (weighted sum)."""
        return (
            self.structural
            + self.behavioral
            + self.semantic
            + self.graph
            + self.complexity
            + self.risk
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "file_path": self.file_path,
            "structural": self.structural,
            "behavioral": self.behavioral,
            "semantic": self.semantic,
            "graph": self.graph,
            "complexity": self.complexity,
            "risk": self.risk,
            "total": self.total,
            "issues": self.issues,
        }


class HotspotCalculator:
    """
    Calculates hotspot scores for code elements.

    MVP implementation focuses on:
    - Structural hotspot: Ruff linting errors (Python only)
    - Semantic hotspot: TODO/FIXME comments (Multi-language via regex)
    - Behavioral hotspot: Git churn
    - Graph hotspot: Coupling (In/Out degrees)
    - Multi-Axis (P2): Logic, Concurrency, Risk
    """

    def __init__(self, project_root: str, config: Any):
        """Initialize calculator with project root and config."""
        self.project_root = Path(project_root).resolve()

        # Load weights from config
        self.config = config
        self._weights = {
            "error": config.hotspot.error_weight,
            "warning": config.hotspot.warning_weight,
            "todo": config.hotspot.todo_weight,
            "fixme": config.hotspot.fixme_weight,
            "hack": getattr(config.hotspot, "hack_weight", 2.0),
            # new weights
            "churn_commit": config.hotspot.churn_commit_weight,
            "import_in": config.hotspot.import_in_weight,
            "import_out": config.hotspot.import_out_weight,
            "centrality": getattr(config.hotspot, "centrality_weight", 0.0),
            # P2 weights
            "logic": getattr(config.hotspot, "logic_weight", 1.0),
            "concurrency": getattr(config.hotspot, "concurrency_weight", 2.0),
            "risk": getattr(config.hotspot, "risk_weight", 1.5),
        }
        self.churn_days = config.hotspot.churn_days
        self.churn_threshold = getattr(config.hotspot, "churn_threshold", 0)

        # Optional graph builder ref
        self._graph_builder = None

        # Pre-calculated maps
        self._churn_map: dict[str, int] = {}
        self._graph_metrics: dict[str, dict] = {}  # {path: {in: N, out: M}}

        # Cache for computed scores
        self._scores: dict[str, HotspotScore] = {}

        # Ruff issues map: {rel_path: [issues]}
        self._ruff_issues_map: dict[str, list[dict]] = {}

        # Regex for TODO/FIXME
        # Matches: (TODO|FIXME|HACK) ... until end of line
        self._todo_pattern = re.compile(r"(TODO|FIXME|HACK)(\(.*\))?:?\s*(.*)", re.IGNORECASE)

    def bind_graph(self, graph_builder):
        """Bind graph builder to enable graph metrics calculation."""
        self._graph_builder = graph_builder
        # Clear graph metrics cache as graph might be different
        self._graph_metrics.clear()

    def reload_config(self, config: Any):
        """Reload weights and settings from config object."""
        self.config = config
        self._weights = {
            "error": config.hotspot.error_weight,
            "warning": config.hotspot.warning_weight,
            "todo": config.hotspot.todo_weight,
            "fixme": config.hotspot.fixme_weight,
            "hack": getattr(config.hotspot, "hack_weight", 2.0),
            "churn_commit": config.hotspot.churn_commit_weight,
            "import_in": config.hotspot.import_in_weight,
            "import_out": config.hotspot.import_out_weight,
            "centrality": getattr(config.hotspot, "centrality_weight", 0.0),
            "logic": getattr(config.hotspot, "logic_weight", 1.0),
            "concurrency": getattr(config.hotspot, "concurrency_weight", 2.0),
            "risk": getattr(config.hotspot, "risk_weight", 1.5),
        }
        self.churn_days = config.hotspot.churn_days
        self.churn_threshold = getattr(config.hotspot, "churn_threshold", 0)
        # Clear score cache since weights changed
        self._scores.clear()
        # Ensure we don't lose the graph builder, or reset if needed
        # self._graph_builder remains as is

    def calculate_file_hotspot(self, file_path: str) -> HotspotScore:
        """
        Calculate hotspot for a single file.

        Args:
            file_path: Path to the Python file (relative to project root, or absolute)

        Returns:
            HotspotScore for the file
        """
        # Normalize: if absolute path, convert to relative
        p = Path(file_path)
        if p.is_absolute():
            with contextlib.suppress(ValueError):
                file_path = str(p.resolve().relative_to(self.project_root))

        node_id = f"file::{file_path}"
        score = HotspotScore(node_id=node_id, file_path=file_path)

        abs_path = self.project_root / file_path
        if not abs_path.exists():
            return score

        # Read content once for multiple analyzers
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""

        # 1. Structural hotspot (Python Only via Ruff)
        if file_path.endswith(".py"):
            # Use precomputed batch results if available, else fall back to single run
            ruff_issues = self._ruff_issues_map.get(file_path)
            if ruff_issues is None:
                ruff_issues = self._run_ruff(abs_path)

            for issue in ruff_issues:
                # Ruff JSON output usually doesn't include "severity".
                # Infer severity from the rule code: E/F are treated as errors.
                code = (issue.get("code") or "").upper()
                sev = "error" if code.startswith(("E", "F")) else "warning"
                weight = self._weights.get(sev, 1.0)
                score.structural += weight
                score.issues.append(
                    {
                        "type": "lint",
                        "code": issue.get("code"),
                        "message": issue.get("message"),
                        "line": issue.get("location", {}).get("row"),
                    }
                )

        # 2. Semantic hotspot from TODO/FIXME (Multi-language)
        # Re-using content if already read? _find_todos reads it again.
        # Optimized: Pass content to _find_todos to avoid re-read?
        # For now, keep as is for compatibility or refactor _find_todos.
        todo_issues = self._find_todos(abs_path)
        for issue in todo_issues:
            score.semantic += issue["weight"]
            score.issues.append(issue)

        # 3. Behavioral hotspot (Git Churn)
        # Using pre-calculated loop or on-demand
        churn_count = self._churn_map.get(file_path, 0)
        # If map is empty (single file calc without map), try to fetch
        if not self._churn_map and churn_count == 0:
            churn_count = self._get_single_file_churn(file_path)

        if churn_count > 0 and churn_count >= self.churn_threshold:
            w = self._weights["churn_commit"]
            val = churn_count * w
            score.behavioral += val
            score.issues.append(
                {
                    "type": "churn",
                    "message": f"High churn: {churn_count} commits in {self.churn_days} days",
                    "count": churn_count,
                    "weight": val,
                }
            )

        # 4. Graph hotspot (Coupling)
        if self._graph_metrics:
            igm = self._graph_metrics.get(file_path)
            if igm:
                in_d = igm["in"]
                out_d = igm["out"]

                val_in = in_d * self._weights["import_in"]
                val_out = out_d * self._weights["import_out"]

                total_coupling = val_in + val_out
                if total_coupling > 0:
                    score.graph += total_coupling
                    score.issues.append(
                        {
                            "type": "coupling",
                            "message": f"Coupling: {in_d} in / {out_d} out",
                            "in": in_d,
                            "out": out_d,
                            "weight": total_coupling,
                        }
                    )

                # 5. Centrality score (PageRank)
                centrality = float(igm.get("centrality", 0.0))
                w_cent = self._weights.get("centrality", 0.0)
                val_cent = centrality * w_cent
                if val_cent > 0:
                    score.graph += val_cent
                    score.issues.append(
                        {
                            "type": "centrality",
                            "message": f"Centrality: {centrality:.3f}",
                            "centrality": centrality,
                            "weight": val_cent,
                        }
                    )

        # 6. Multi-Axis Scoring (P2)
        if content:
            from .scorers import ConcurrencyScorer, LogicScorer, RiskScorer

            # Logic (Score goes to 'complexity')
            logic_res = LogicScorer(content, file_path).score()
            if logic_res.score > 0:
                w = self._weights.get("logic", 1.0)
                # normalize internal score (which might be raw) and apply weight
                val = logic_res.score * w
                score.complexity += val
                for i in logic_res.issues:
                    i["weight"] = i.get("weight", 0) * w
                    score.issues.append(i)

            # Concurrency (Score goes to 'complexity')
            conc_res = ConcurrencyScorer(content, file_path).score()
            if conc_res.score > 0:
                w = self._weights.get("concurrency", 1.0)
                val = conc_res.score * w
                score.complexity += val  # Concurrency adds to complexity in this model
                for i in conc_res.issues:
                    i["weight"] = i.get("weight", 0) * w
                    score.issues.append(i)

            # Risk (Score goes to 'risk')
            risk_res = RiskScorer(content, file_path).score()
            if risk_res.score > 0:
                w = self._weights.get("risk", 1.0)
                val = risk_res.score * w
                score.risk += val
                for i in risk_res.issues:
                    i["weight"] = i.get("weight", 0) * w
                    score.issues.append(i)

        self._scores[node_id] = score
        return score

    def calculate_all(self, file_paths: list[str]) -> dict[str, HotspotScore]:
        """
        Calculate hotspot for multiple files.
        Pre-calculates churn and graph metrics for performance.
        """
        # Clear cache for determinism - avoid stale results from previous runs
        self._scores.clear()

        # Sort for deterministic ordering
        file_paths = sorted(file_paths)

        # Pre-calc churn
        self._churn_map = self._get_git_churn_map(self.churn_days)

        # Pre-calc lint (Ruff batch)
        self._precompute_ruff_issues(file_paths)

        # Pre-calc graph metrics
        if self._graph_builder:
            self._graph_metrics = self._calculate_graph_metrics()

        results = {}
        for path in file_paths:
            score = self.calculate_file_hotspot(path)
            results[score.node_id] = score
        return results

    def _get_single_file_churn(self, file_path: str) -> int:
        try:
            cmd = [
                "git",
                "log",
                f"--since={self.churn_days} days ago",
                "--oneline",
                "--",
                file_path,
            ]
            res = safe_shell(cmd, cwd=str(self.project_root), timeout=10)
            return len(res.stdout.strip().splitlines())
        except Exception:
            return 0

    def _get_git_churn_map(self, days: int) -> dict[str, int]:
        """Return {file_path: commit_count} for last N days."""
        churn: dict[str, int] = {}
        try:
            # git log --name-only --format="" --since="30 days ago"
            cmd = ["git", "log", "--name-only", "--format=", f"--since={days} days ago"]
            res = safe_shell(cmd, cwd=str(self.project_root), timeout=15)
            if not res.success:
                return {}

            for line in res.stdout.splitlines():
                path = line.strip()
                if path:
                    churn[path] = churn.get(path, 0) + 1
        except Exception:
            pass
        return churn

    def _calculate_graph_metrics(self) -> dict[str, dict]:
        """Compute in-degree, out-degree, and PageRank centrality for all files."""
        # This requires traversing the graph.
        # graph_builder gives us nodes and edges.
        # We need "file-level" dependencies.
        # Since the graph might be function-level, we aggregate.

        metrics: dict[str, dict] = {}

        # We need access to the graph structure.
        # Assuming graph_builder has a 'graph' attribute (rustworkx or networkx)
        if not self._graph_builder or not hasattr(self._graph_builder, "graph"):
            return {}

        g = self._graph_builder.graph

        try:
            # 1. Build Index -> File map
            node_file_map = {}
            for idx in g.node_indices():
                n_data = g[idx]  # GraphNode (BaseNode)

                # Check known attributes
                fpath = None
                if hasattr(n_data, "relative_path"):  # FileNode
                    fpath = n_data.relative_path
                elif hasattr(n_data, "file_path"):  # Class/Function/Query
                    fpath = n_data.file_path

                # Fallback to ID parse
                if not fpath:
                    parts = n_data.id.split("::")
                    if len(parts) >= 2:
                        fpath = parts[1]

                if fpath:
                    node_file_map[idx] = fpath
                    if fpath not in metrics:
                        metrics[fpath] = {"in": 0, "out": 0, "centrality": 0.0}

            # 2. Iterate edges and collect unique file->file edges
            from ..core.edges import EdgeType

            file_edges: set[tuple[str, str]] = set()

            # rustworkx.PyDiGraph stores edge payload as the "weight".
            # Use out_edges() to reliably obtain (u, v, edge_data).
            for u_idx in g.node_indices():
                for _, v_idx, edge_data in g.out_edges(u_idx):
                    if edge_data is None:
                        continue

                    e_type = getattr(edge_data, "edge_type", None)
                    # Count IMPORTS and CALLS as dependencies (file-level coupling)
                    if e_type not in (EdgeType.IMPORTS, EdgeType.CALLS):
                        continue

                    u_file = node_file_map.get(u_idx)
                    v_file = node_file_map.get(v_idx)

                    if not u_file or not v_file or u_file == v_file:
                        continue

                    # Ensure both are initialized
                    metrics.setdefault(u_file, {"in": 0, "out": 0, "centrality": 0.0})
                    metrics.setdefault(v_file, {"in": 0, "out": 0, "centrality": 0.0})

                    key = (u_file, v_file)
                    if key in file_edges:
                        continue

                    # Track unique file-level edge for both coupling + PageRank
                    file_edges.add(key)

                    # u -> v means u depends on v
                    metrics[u_file]["out"] += 1
                    metrics[v_file]["in"] += 1

            # 3. Compute PageRank on file-level graph
            if file_edges:
                self._compute_file_pagerank(metrics, file_edges)

        except Exception as e:
            # Log errors instead of silently ignoring
            import logging

            logger = logging.getLogger(__name__)
            logger.debug("Graph coupling metrics calculation failed: %s", e, exc_info=True)

        return metrics

    def _compute_file_pagerank(
        self, metrics: dict[str, dict], file_edges: set[tuple[str, str]]
    ) -> None:
        """Compute PageRank centrality for file-level graph."""
        try:
            import rustworkx as rx
        except ImportError:
            return  # rustworkx not available

        # Build file-level graph
        file_graph = rx.PyDiGraph()
        file_to_idx: dict[str, int] = {}

        for u_file, v_file in file_edges:
            if u_file not in file_to_idx:
                file_to_idx[u_file] = file_graph.add_node(u_file)
            if v_file not in file_to_idx:
                file_to_idx[v_file] = file_graph.add_node(v_file)
            file_graph.add_edge(file_to_idx[u_file], file_to_idx[v_file], None)

        # Compute PageRank
        try:
            pr = rx.pagerank(file_graph)
        except Exception:
            return

        # Normalize: multiply by number of files for interpretable centrality
        n_files = len(file_to_idx)
        for fpath, idx in file_to_idx.items():
            raw_pr = pr.get(idx, 0.0)
            # Store normalized centrality (average file would be 1.0)
            metrics[fpath]["centrality"] = raw_pr * n_files

    def _precompute_ruff_issues(self, file_paths: list[str]) -> None:
        """Run Ruff on the entire project or subset and populate issue map."""
        self._ruff_issues_map.clear()
        python_files = [f for f in file_paths if f.endswith(".py")]
        if not python_files:
            return

        try:
            # We run on the project root but tell ruff to only check specific files if the list is small,
            # otherwise check everything for maximum efficiency.
            cmd = ["ruff", "check", "--output-format", "json"]
            if len(python_files) < 100:
                cmd.extend(python_files)
            else:
                cmd.append(".")

            result = safe_shell(
                cmd,
                cwd=str(self.project_root),
                timeout=max(30, self.config.hotspot.analysis_timeout * 2),
            )

            if result.stdout:
                issues = json.loads(result.stdout)
                for issue in issues:
                    # Ruff returns 'filename' or 'path' relative to CWD
                    f = issue.get("filename") or issue.get("path")
                    if f:
                        # Normalize path to relative posix
                        f_rel = Path(f).as_posix()
                        if f_rel.startswith("./"):
                            f_rel = f_rel[2:]
                        self._ruff_issues_map.setdefault(f_rel, []).append(issue)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.debug("Ruff batch precompute failed: %s", e)

    def get_high_hotspot_nodes(self, threshold: float | None = None) -> list[HotspotScore]:
        """Get nodes with hotspot above threshold."""
        if threshold is None:
            threshold = self.config.hotspot.high_hotspot_threshold
        return [s for s in self._scores.values() if s.total >= threshold]

    def _run_ruff(self, file_path: Path) -> list[dict]:
        """Run Ruff linter on a file and return issues."""
        try:
            result = safe_shell(
                ["ruff", "check", "--output-format", "json", str(file_path)],
                timeout=self.config.hotspot.analysis_timeout,
            )

            if result.stdout:
                issues = json.loads(result.stdout)
                return issues
            return []

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            # Ruff not installed or timeout - return empty, but maybe we should warn?
            # For now, if tool missing, we silent fail to not spam.
            return []
        except Exception as e:
            # Generic error (e.g. non-zero exit code if check fails badly, though ruff check usually exits 0 or 1)
            # If ruff crashes or something else, return a system warning.
            return [
                {
                    "type": "warning",
                    "code": "Y001",
                    "message": f"Analysis failed: {str(e)}",
                    "line": 0,
                    "severity": "warning",
                }
            ]

    def _find_todos(self, file_path: Path) -> list[dict]:
        """Find TODO/FIXME/HACK in a file, but only inside comments."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        issues = []
        # Iterate over comments only to avoid false positives in string literals
        for line_no, comment_text in self._iter_comment_texts(file_path, content):
            match = self._todo_pattern.search(comment_text)
            if match:
                tag = match.group(1).upper()
                message = match.group(3).strip()

                weight = 1.0
                if tag == "TODO":
                    weight = self._weights["todo"]
                    msg_type = "todo"
                elif tag == "FIXME":
                    weight = self._weights["fixme"]
                    msg_type = "fixme"
                else:  # HACK
                    weight = self._weights["hack"]
                    msg_type = "hack"

                issues.append(
                    {
                        "type": msg_type,
                        "message": message or f"{tag} found",
                        "line": line_no,
                        "weight": weight,
                    }
                )

        return issues

    def _iter_comment_texts(self, file_path: Path, content: str) -> Iterator[tuple[int, str]]:
        """
        Yield (line_no, comment_text) pairs for the file.
        Extracts comments while avoiding matches inside string literals.
        """
        suffix = file_path.suffix.lower()

        # Python: use tokenize for 100% accuracy
        if suffix == ".py":
            yield from self._iter_python_comments(content)
            return

        # C-like languages: // and /* */
        c_like = {
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".c",
            ".cc",
            ".cpp",
            ".h",
            ".hpp",
            ".cs",
            ".go",
            ".rs",
            ".swift",
            ".php",
            ".kt",
        }
        if suffix in c_like:
            yield from self._iter_c_like_comments(
                content,
                line_prefix="//",
                block_start="/*",
                block_end="*/",
                allow_regex_literals=suffix in {".js", ".ts", ".jsx", ".tsx"},
            )
            return

        # Hash-comment languages: # ...
        hash_like = {
            ".rb",
            ".sh",
            ".bash",
            ".zsh",
            ".pyi",
            ".toml",
            ".yml",
            ".yaml",
            ".ini",
            ".cfg",
            ".pl",
            ".pm",
        }
        if suffix in hash_like:
            yield from self._iter_hash_line_comments(content)
            return

        # SQL: -- and /* */
        if suffix in {".sql"}:
            yield from self._iter_c_like_comments(
                content, line_prefix="--", block_start="/*", block_end="*/"
            )
            return

        # Default fallback: treat # as comment marker
        # Better to miss than produce noise
        yield from self._iter_hash_line_comments(content)

    def _iter_python_comments(self, content: str) -> Iterator[tuple[int, str]]:
        """Extract comments from Python source using tokenize."""
        try:
            for tok in tokenize.generate_tokens(io.StringIO(content).readline):
                if tok.type == tokenize.COMMENT:
                    line_no = tok.start[0]
                    txt = tok.string.lstrip("#").strip()
                    if txt:
                        yield (line_no, txt)
        except tokenize.TokenError:
            # Syntax error in file - fall back to hash parsing
            yield from self._iter_hash_line_comments(content)

    def _iter_hash_line_comments(self, content: str) -> Iterator[tuple[int, str]]:
        """Extract # comments, basic line-by-line."""
        for i, line in enumerate(content.splitlines(), start=1):
            if "#" not in line:
                continue
            # Skip shebang
            if i == 1 and line.startswith("#!"):
                continue
            idx = line.find("#")
            txt = line[idx + 1 :].strip()
            if txt:
                yield (i, txt)

    def _iter_c_like_comments(
        self,
        content: str,
        line_prefix: str,
        block_start: str,
        block_end: str,
        allow_regex_literals: bool = False,
    ) -> Iterator[tuple[int, str]]:
        """
        Extract comments from C-like languages.
        Handles // line comments and /* block comments */.
        Avoids matching inside string literals.
        For JS/TS, optionally avoids false positives inside regex literals.
        """
        i = 0
        line = 1
        n = len(content)
        state = "code"  # code | string | regex | block_comment
        str_delim = ""
        buf = ""
        buf_line = 1
        regex_in_class = False
        regex_escaped = False

        # Heuristic: regex literals are typically allowed after these tokens.
        regex_prev_ok = {
            "",
            "(",
            "[",
            "{",
            "=",
            ":",
            ",",
            ";",
            "!",
            "&",
            "|",
            "?",
            "~",
            "^",
            "<",
            ">",
            "+",
            "-",
            "*",
            "%",
            "\n",
        }

        while i < n:
            ch = content[i]

            if state == "code":
                # Check for strings
                if ch in ("'", '"', "`"):
                    state = "string"
                    str_delim = ch
                    i += 1
                    continue

                # Check for line comment
                if line_prefix and content[i:].startswith(line_prefix):
                    j = i + len(line_prefix)
                    k = j
                    while k < n and content[k] != "\n":
                        k += 1
                    txt = content[j:k].strip()
                    if txt:
                        yield (line, txt)
                    i = k
                    continue

                # Check for block comment
                if block_start and content[i:].startswith(block_start):
                    # Start block
                    state = "block_comment"
                    buf = ""
                    buf_line = line
                    i += len(block_start)
                    continue

                # JS/TS: Check for regex literal start (avoid treating /.../ as comments)
                if allow_regex_literals and ch == "/":
                    nxt = content[i + 1] if i + 1 < n else ""
                    if nxt and nxt not in ("/", "*"):
                        # Ensure it's not division
                        p = i - 1
                        while p >= 0 and content[p] in " \t\r\n":
                            p -= 1
                        prev = content[p] if p >= 0 else ""
                        if prev in regex_prev_ok:
                            state = "regex"
                            regex_in_class = False
                            regex_escaped = False
                            i += 1
                            continue

                # Newline
                if ch == "\n":
                    line += 1
                i += 1
                continue

            if state == "string":
                # Handle escapes
                if ch == "\\" and i + 1 < n:
                    if content[i + 1] == "\n":
                        line += 1
                    i += 2
                    continue
                if ch == str_delim:
                    state = "code"
                    i += 1
                    continue
                if ch == "\n":
                    line += 1
                i += 1
                continue

            if state == "regex":
                # We only need to skip over the literal so comment tokens inside it are ignored.
                if ch == "\n":
                    # Implicit end of regex at newline if not handled, though typically syntax error
                    line += 1
                    regex_escaped = False
                    state = "code"  # Reset to code on newline safety
                    i += 1
                    continue
                if regex_escaped:
                    regex_escaped = False
                    i += 1
                    continue
                if ch == "\\":
                    regex_escaped = True
                    i += 1
                    continue
                if ch == "[":
                    regex_in_class = True
                    i += 1
                    continue
                if ch == "]" and regex_in_class:
                    regex_in_class = False
                    i += 1
                    continue
                if ch == "/" and not regex_in_class:
                    state = "code"
                    i += 1
                    # Skip flags (e.g., /re/gi)
                    while i < n and content[i].isalpha():
                        i += 1
                    continue
                i += 1
                continue

            if state == "block_comment":
                # Check for block end
                if block_end and content[i:].startswith(block_end):
                    # Flush buffer
                    txt = buf.strip()
                    if txt:
                        yield (buf_line, txt)
                    buf = ""
                    state = "code"
                    i += len(block_end)
                    continue
                if ch == "\n":
                    # Flush line
                    txt = buf.strip()
                    if txt:
                        yield (buf_line, txt)
                    buf = ""
                    line += 1
                    buf_line = line
                    i += 1
                    continue
                buf += ch
                i += 1
                continue

    def aggregate_for_function(
        self,
        function: Any,  # FunctionNode
        file_score: HotspotScore,
    ) -> HotspotScore:
        """
        Aggregate hotspot score for a specific function.

        Filters issues that fall within the function's line range.
        """
        score = HotspotScore(node_id=function.id)

        for issue in file_score.issues:
            line = issue.get("line")
            if line and function.line_start <= line <= function.line_end:
                # Check issue type
                t = issue["type"]
                if t == "lint":
                    # Ruff: E*/F* are errors, everything else is warning
                    code = (issue.get("code") or "").upper()
                    severity = "error" if code.startswith(("E", "F")) else "warning"
                    score.structural += self._weights.get(severity, 1.0)
                else:
                    # Semantic usually (todo/fixme)
                    score.semantic += issue.get("weight", 1.0)
                score.issues.append(issue)

        return score
