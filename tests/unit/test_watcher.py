"""
Tests for WatcherService.
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codex_mesh.services.watcher_service import WatcherService


@pytest.fixture
def mock_graph_builder():
    return MagicMock()


@pytest.mark.asyncio
async def test_watcher_lifecycle(mock_graph_builder):
    root = Path("/tmp/test")
    watcher = WatcherService(root, mock_graph_builder)

    # Test Start
    await watcher.start()
    assert watcher._watch_task is not None
    assert not watcher._watch_task.done()

    # Test Stop
    await watcher.stop()
    assert watcher._watch_task is None


@pytest.mark.asyncio
async def test_watcher_process_change(mock_graph_builder):
    root = Path("/tmp/test")
    # Use short debounce for testing
    watcher = WatcherService(root, mock_graph_builder, debounce_seconds=0.01)

    # Mock registry to allow the file
    mock_graph_builder.registry.get_for_path.return_value = "some_extractor"

    # Mock awatch to yield one change set then stop
    # awatch yields sets of (Change, path)
    from watchfiles import Change

    async def mock_awatch_gen(*args, **kwargs):
        yield {(Change.modified, "/tmp/test/foo.py")}
        # Simulate stop event wait if needed, or just exit

    # We patch awatch directly
    with (
        patch("codex_mesh.services.watcher_service.awatch", side_effect=mock_awatch_gen),
        patch("pathlib.Path.is_file", return_value=True),
    ):
        # Start watcher
        await watcher.start()

        # Wait a bit for the loop and debounce to process
        await asyncio.sleep(0.1)

        # Stop watcher
        await watcher.stop()

    # Verify build called (Full rebuild strategy)
    mock_graph_builder.build.assert_called()
