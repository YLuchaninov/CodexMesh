"""
Pytest configuration and shared fixtures.
"""

import pytest

# Mock dependencies if missing
# NOTE: Removed global sys.modules mocks to prevent masking missing dependencies.
# Integration tests should use pytest.importorskip() or specific fixtures.


@pytest.fixture
def mock_config():
    """Mock configuration for tests."""

    class MockConfig:
        class Hotspot:
            error_weight = 10.0
            warning_weight = 5.0
            todo_weight = 2.0
            fixme_weight = 5.0
            hack_weight = 2.0
            churn_days = 30
            churn_threshold = 0  # No threshold for tests
            churn_commit_weight = 0.5
            import_in_weight = 0.3
            import_out_weight = 0.2
            centrality_weight = 0.2

            # P2 weights
            logic_weight = 1.0
            concurrency_weight = 2.0
            risk_weight = 1.5

            high_hotspot_threshold = 5.0
            analysis_timeout = 30

        hotspot = Hotspot()

    return MockConfig()
