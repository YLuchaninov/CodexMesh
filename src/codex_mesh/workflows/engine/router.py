"""
Intent Router.
Classifies user queries into intents using embedding similarity or heuristics.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

try:
    from fastembed import TextEmbedding

    HAS_FASTEMBED = True
except ImportError:
    HAS_FASTEMBED = False


@dataclass(frozen=True)
class Match:
    intent_id: str
    score: float


def _cosine(a: list[float], b: list[float]) -> float:
    da = sum(x * x for x in a) ** 0.5
    db = sum(x * x for x in b) ** 0.5
    if da == 0 or db == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=False)) / (da * db)


class IntentRouter:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", threshold: float = 0.55):
        self._threshold = threshold
        self._index: list[tuple[str, list[float]]] = []
        self._embedder = None
        self._intents: list[dict[str, Any]] = []
        self._intent_tokens: dict[str, set[str]] = {}

        if HAS_FASTEMBED:
            try:
                self._embedder = TextEmbedding(model_name=model_name)
            except Exception as e:
                logger.warning("Failed to load embedding model: %s", e)

    def build_index(self, intents: list[dict[str, Any]]) -> None:
        """
        intents: list of dicts with keys id, description, examples
        """
        self._index.clear()
        self._intents = list(intents or [])

        # Build token sets for heuristic fallback (always)
        self._intent_tokens.clear()

        def tok(s: str) -> set[str]:
            parts = re.findall(r"[a-zA-Z0-9_]{3,}", (s or "").lower())
            stop = {
                "the",
                "and",
                "for",
                "with",
                "from",
                "into",
                "that",
                "this",
                "your",
                "you",
                "are",
                "how",
                "what",
                "when",
                "where",
            }
            return {p for p in parts if p not in stop}

        for it in self._intents:
            payload = " ".join(
                [it.get("id", ""), it.get("description", "")] + list(it.get("examples", [])[:5])
            )
            self._intent_tokens[it.get("id", "")] = tok(payload)

        # Semantic index only if embedder exists
        if not self._embedder:
            return

        texts: list[str] = []
        ids: list[str] = []
        for it in intents:
            # Create a rich representation for embedding
            payload = " ".join(
                [it.get("id", ""), it.get("description", "")] + list(it.get("examples", [])[:5])
            ).strip()
            if payload:
                texts.append(payload)
                ids.append(it["id"])

        if not texts:
            return

        try:
            vectors = list(self._embedder.embed(texts))
            for intent_id, vec in zip(ids, vectors, strict=False):
                self._index.append((intent_id, list(vec)))
        except Exception as e:
            logger.error("Error building intent index: %s", e, exc_info=True)

    def match(self, query: str) -> Match | None:
        # 1) semantic match (if available)
        if self._index and self._embedder:
            try:
                qv_raw = list(self._embedder.embed([query]))[0]
                qv: list[float] = qv_raw.tolist() if hasattr(qv_raw, "tolist") else list(qv_raw)  # type: ignore

                best = None
                for intent_id, iv in self._index:
                    s = _cosine(qv, iv)
                    if best is None or s > best.score:
                        best = Match(intent_id=intent_id, score=s)

                if best and best.score >= self._threshold:
                    return best
            except Exception as e:
                # In production this might be logged, in tests it helps debugging
                if "PYTEST_CURRENT_TEST" in os.environ:
                    raise
                logger.warning("Error in intent matching: %s", e, exc_info=True)

        # 2) heuristic fallback
        q = (query or "").lower()
        phrase_map = [
            (("dead code", "unused", "unreachable"), "intent.dead_code"),
            (("impact", "blast radius", "what breaks"), "intent.change_impact"),
            (("dependency tree", "depends on"), "intent.graph_dependency_tree"),
            (("dependency path", "path between", "between"), "intent.graph_path"),
            (("hotspot", "tension", "risk"), "intent.hotspots_report"),
            (("overview", "repo map", "structure"), "intent.codebase_overview"),
            (("security", "auth", "cors", "token"), "intent.security_review"),
            (("refactor", "cleanup"), "intent.refactor_guidance"),
            (("architecture", "layering", "cycles"), "intent.architecture_consistency"),
            (("capabilities", "what can you do", "tools"), "intent.mcp_capabilities"),
            (("find symbol", "definition of", "where is"), "intent.symbol_lookup"),
        ]
        for phrases, iid in phrase_map:
            if any(p in q for p in phrases):
                return Match(intent_id=iid, score=0.90)

        qt = set(re.findall(r"[a-zA-Z0-9_]{3,}", q))
        best_id = None
        best_score = 0.0
        for iid, toks in self._intent_tokens.items():
            if not iid:
                continue
            inter = len(qt & toks)
            if inter == 0:
                continue
            score = inter / max(6, len(qt))
            if score > best_score:
                best_score = score
                best_id = iid
        if best_id and best_score >= 0.12:
            return Match(intent_id=best_id, score=float(best_score))

        return None

    def route(self, query: str) -> tuple[str | None, dict[str, Any]]:
        """Legacy route method compatibility."""
        match = self.match(query)
        if match:
            return match.intent_id, {}
        return None, {}
