"""Hotspot weight auto-calibrator.

Calibrates hotspot weights based on repo-specific distribution to achieve
a target hotspot rate (e.g., top 5% of files flagged as hotspots).
"""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .hotspot import HotspotScore


@dataclass
class HotspotCalibrationResult:
    """Result of hotspot weight calibration."""

    recommended: dict[str, Any] = field(default_factory=dict)
    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)
    applied: bool = False


class HotspotWeightCalibrator:
    """Calibrate hotspot weights based on repository distribution.

    Uses deterministic sampling to select representative files,
    then scales weights to achieve a target hotspot rate.
    """

    def __init__(self, config: Any):
        self.config = config

    def calibrate(
        self,
        scores: Iterable["HotspotScore"],
        *,
        target_hotspot_rate: float = 0.05,
        percentile: int = 95,
        max_files: int = 800,
    ) -> HotspotCalibrationResult:
        """Calibrate weights based on score distribution.

        Args:
            scores: Iterable of HotspotScore objects
            target_hotspot_rate: Target fraction of files to flag (e.g., 0.05 = top 5%)
            percentile: Percentile to use for setting threshold
            max_files: Maximum files to consider for calibration

        Returns:
            HotspotCalibrationResult with recommended weights
        """
        # Convert to list and sample if too many
        score_list = list(scores)
        if len(score_list) > max_files:
            score_list = self._stable_sample(score_list, max_files)

        if not score_list:
            return HotspotCalibrationResult()

        # Get current configuration snapshot
        before = self._get_config_snapshot()

        # Calculate component distributions
        structural_scores = [s.structural for s in score_list]
        behavioral_scores = [s.behavioral for s in score_list]
        semantic_scores = [s.semantic for s in score_list]
        graph_scores = [s.graph for s in score_list]
        total_scores = [s.total for s in score_list]

        # Get percentile values for normalization
        p_structural = self._percentile(structural_scores, percentile)
        p_behavioral = self._percentile(behavioral_scores, percentile)
        p_semantic = self._percentile(semantic_scores, percentile)
        p_graph = self._percentile(graph_scores, percentile)

        # Calculate current component shares
        total_sum = sum(total_scores)
        if total_sum == 0:
            return HotspotCalibrationResult(before=before, recommended=before)

        shares = {
            "structural": sum(structural_scores) / total_sum,
            "behavioral": sum(behavioral_scores) / total_sum,
            "semantic": sum(semantic_scores) / total_sum,
            "graph": sum(graph_scores) / total_sum,
        }

        # Calculate threshold for target hotspot rate
        n_target = max(1, int(len(score_list) * target_hotspot_rate))
        sorted_totals = sorted(total_scores, reverse=True)
        recommended_threshold = sorted_totals[min(n_target - 1, len(sorted_totals) - 1)]

        # Create recommended configuration
        recommended = dict(before)
        recommended["high_hotspot_threshold"] = round(recommended_threshold, 2)

        # Component normalization info (for UI/debugging)
        recommended["_calibration_info"] = {
            "files_analyzed": len(score_list),
            "target_rate": target_hotspot_rate,
            "percentile": percentile,
            "component_shares": shares,
            "percentile_values": {
                "structural": round(p_structural, 2),
                "behavioral": round(p_behavioral, 2),
                "semantic": round(p_semantic, 2),
                "graph": round(p_graph, 2),
            },
        }

        # After configuration = what it would look like after applying
        after = dict(recommended)

        return HotspotCalibrationResult(
            recommended=recommended,
            before=before,
            after=after,
            applied=False,
        )

    def _get_config_snapshot(self) -> dict[str, Any]:
        """Get current hotspot config as dict."""
        hc = self.config.hotspot
        return {
            "error_weight": getattr(hc, "error_weight", 5.0),
            "warning_weight": getattr(hc, "warning_weight", 1.0),
            "todo_weight": getattr(hc, "todo_weight", 3.0),
            "fixme_weight": getattr(hc, "fixme_weight", 4.0),
            "hack_weight": getattr(hc, "hack_weight", 2.0),
            "churn_days": getattr(hc, "churn_days", 30),
            "churn_threshold": getattr(hc, "churn_threshold", 5),
            "churn_commit_weight": getattr(hc, "churn_commit_weight", 0.5),
            "import_in_weight": getattr(hc, "import_in_weight", 0.3),
            "import_out_weight": getattr(hc, "import_out_weight", 0.2),
            "centrality_weight": getattr(hc, "centrality_weight", 0.2),
            "high_hotspot_threshold": getattr(hc, "high_hotspot_threshold", 5.0),
            "analysis_timeout": getattr(hc, "analysis_timeout", 30),
        }

    def _stable_sample(self, scores: list["HotspotScore"], max_n: int) -> list["HotspotScore"]:
        """Sample files deterministically based on file path hash."""

        def hash_key(score: "HotspotScore") -> str:
            # Use SHA256 hash of file path for stable ordering
            path = score.file_path or score.node_id
            return hashlib.sha256(path.encode()).hexdigest()

        # Sort by hash for reproducibility
        sorted_scores = sorted(scores, key=hash_key)
        # Take evenly spaced samples
        step = max(1, len(sorted_scores) // max_n)
        return sorted_scores[::step][:max_n]

    @staticmethod
    def _percentile(values: list[float], p: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        k = (n - 1) * p / 100
        f = int(k)
        c = f + 1
        if c >= n:
            return sorted_vals[-1]
        return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)
