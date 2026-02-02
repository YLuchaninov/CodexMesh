"""Tests for HotspotWeightCalibrator."""

from dataclasses import dataclass

import pytest

from codex_mesh.metrics.hotspot_tuner import HotspotWeightCalibrator


@dataclass
class MockHotspot:
    file_path: str
    structural: float = 0.0
    behavioral: float = 0.0
    semantic: float = 0.0
    graph: float = 0.0
    total: float = 0.0
    node_id: str = "id"


@pytest.fixture
def tuner_config(mock_config):
    return mock_config


def test_calibrate_empty(tuner_config):
    """Test calibration with no scores."""
    calibrator = HotspotWeightCalibrator(tuner_config)
    result = calibrator.calibrate([], target_hotspot_rate=0.05)
    assert not result.recommended
    assert not result.before
    assert not result.applied


def test_calibrate_threshold(tuner_config):
    """Test that recommended threshold is calculated correctly."""
    calibrator = HotspotWeightCalibrator(tuner_config)

    # Create 100 scores with linearly increasing total scores
    scores = []
    for i in range(100):
        # file_0 has total 0, file_99 has total 99
        s = MockHotspot(file_path=f"file_{i}", total=float(i))
        # Add component scores for realism
        s.structural = i * 0.5
        s.behavioral = i * 0.3
        s.semantic = i * 0.1
        s.graph = i * 0.1
        scores.append(s)

    # Target top 5% -> Should pick threshold around 94-95
    # sorted: 99, 98, 97, 96, 95 (top 5) -> threshold should be 95
    result = calibrator.calibrate(scores, target_hotspot_rate=0.05, percentile=95)

    assert result.recommended
    assert "high_hotspot_threshold" in result.recommended

    # With 100 items, target_rate 0.05 means n_target = 5
    # Logic:
    # sorted_totals = [99, 98, ..., 0]
    # index = min(5-1, 99) = 4
    # value = sorted_totals[4] = 95
    assert result.recommended["high_hotspot_threshold"] == 95.0

    # Check that info is populated
    info = result.recommended["_calibration_info"]
    assert info["files_analyzed"] == 100
    assert info["target_rate"] == 0.05


def test_stable_sampling(tuner_config):
    """Test that sampling is deterministic."""
    calibrator = HotspotWeightCalibrator(tuner_config)

    scores = []
    for i in range(100):
        scores.append(MockHotspot(file_path=f"file_{i}", total=float(i)))

    # Sample 10 items
    result1 = calibrator._stable_sample(scores, 10)
    result2 = calibrator._stable_sample(scores, 10)

    assert len(result1) == 10
    assert len(result2) == 10

    # Check identity
    paths1 = [s.file_path for s in result1]
    paths2 = [s.file_path for s in result2]
    assert paths1 == paths2


def test_percentile_calculation():
    """Test internal percentile logic."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    # 50th percentile (median) of 1..10 is 5.5
    # Our simple logic: (10-1)*0.5 = 4.5 -> index 4 and 5 -> (5+6)/2 = 5.5
    p50 = HotspotWeightCalibrator._percentile(values, 50)
    assert p50 == 5.5

    # 90th percentile -> index 8.1 -> between 9 (idx 8) and 10 (idx 9)
    # 0.1 * (10-9) + 9 = 9.1
    p90 = HotspotWeightCalibrator._percentile(values, 90)
    assert 9.0 <= p90 <= 10.0
