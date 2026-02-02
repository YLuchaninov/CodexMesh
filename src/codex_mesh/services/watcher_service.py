"""
File Watcher Service.

Monitors the project directory for changes and triggers graph updates.
"""

import asyncio
import contextlib
import inspect
import logging
from pathlib import Path

from watchfiles import Change, awatch

from ..core.graph import CodeGraphBuilder

logger = logging.getLogger(__name__)


class WatcherService:
    def __init__(
        self,
        project_root: Path,
        graph_builder: CodeGraphBuilder,
        *,
        on_rebuild=None,
        debounce_seconds: float = 1.0,
    ):
        self.project_root = project_root
        self.graph_builder = graph_builder
        self._stop_event = asyncio.Event()
        self._watch_task: asyncio.Task | None = None
        self._rebuild_task: asyncio.Task | None = None
        self._on_rebuild = on_rebuild
        self._debounce_seconds = debounce_seconds

    async def start(self) -> None:
        """Start the file watcher in a background task."""
        if self._watch_task and not self._watch_task.done():
            return

        self._stop_event.clear()
        self._watch_task = asyncio.create_task(self._watch_loop())
        logger.info(f"Started file watcher for {self.project_root}")

    async def stop(self) -> None:
        """Stop the file watcher."""
        if self._watch_task:
            self._stop_event.set()
            # We can't easily cancel awatch, but we can stop processing.
            # awatch supports stop_event in newer versions, or we cancel the task.
            self._watch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._watch_task
            self._watch_task = None

            if self._rebuild_task and not self._rebuild_task.done():
                self._rebuild_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._rebuild_task
                self._rebuild_task = None

            logger.info("Stopped file watcher")

    def _schedule_rebuild(self) -> None:
        if self._rebuild_task and not self._rebuild_task.done():
            self._rebuild_task.cancel()
        self._rebuild_task = asyncio.create_task(self._debounced_rebuild())

    async def _debounced_rebuild(self) -> None:
        try:
            await asyncio.sleep(self._debounce_seconds)
            logger.info("Rebuilding graph due to file changes...")
            await asyncio.to_thread(self.graph_builder.build)

            if self._on_rebuild is not None:
                try:
                    res = self._on_rebuild()
                    if inspect.isawaitable(res):
                        await res
                except Exception:
                    logger.warning("Watcher on_rebuild callback failed", exc_info=True)
            logger.info("Graph rebuild complete")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("Graph rebuild failed", exc_info=True)

    async def _watch_loop(self) -> None:
        """Main watching loop."""
        try:
            # We filter for relevant files
            async for changes in awatch(self.project_root, stop_event=self._stop_event):
                # Reload ignore rules on every batch to capture .gitignore changes
                from ..core.ignore import IgnoreMatcher

                ignore = IgnoreMatcher.load(self.project_root)

                trigger_rebuild = False
                for change_type, path_str in changes:
                    path = Path(path_str)

                    # Check ignore rules
                    # is_dir=None lets pathspec decide or match typically
                    # If path exists and is dir, we can pass True.
                    # If deleted, we can't check FS.
                    is_d = path.is_dir() if path.exists() else None
                    if ignore.is_ignored(path, is_dir=is_d):
                        continue

                    # Handle deletions which won't pass is_file()
                    if change_type == Change.deleted:
                        # Use registry to check if extension was tracked
                        if not self.graph_builder.registry.supports_extension(path.suffix):
                            continue
                        # If it was a source file, we should likely rebuild
                        trigger_rebuild = True
                        break

                    # Only rebuild if the file is one we care about (or would care about)
                    if not path.is_file():
                        continue
                    if self.graph_builder.registry.get_for_path(path) is None:
                        continue

                    trigger_rebuild = True
                    break  # minimal trigger

                if trigger_rebuild:
                    self._schedule_rebuild()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Watcher loop failed: {e}", exc_info=True)
