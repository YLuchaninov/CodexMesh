"""
Intent Registry.
Loads and manages available intents.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntentDefinition:
    id: str
    title: str
    description: str
    slots: dict[str, Any]
    input_schema: dict[str, Any]
    examples: list[str]
    workflow: dict[str, Any]


class IntentRegistry:
    def __init__(self, intents_dir: str):
        self._dir = Path(intents_dir)
        self._intents: dict[str, IntentDefinition] = {}

    def load(self) -> None:
        self._intents.clear()
        if not self._dir.exists():
            # Fallback: try loading from package resources (installed wheel)
            # This handles the case where users pip install and run without valid CWD workflows
            try:
                # For Python 3.9+
                pkg_files = resources.files("codex_mesh.workflows.definitions")
                # We can't glob directly on a MultiplexedPath in all versions,
                # so we iterate.
                # Note: We need to ensure we are iterating over the actual resource files.
                logger.info("Loading built-in workflows from package resources.")
                for res in pkg_files.iterdir():
                    if res.name.endswith(".json"):
                        with res.open("r", encoding="utf-8") as f:
                            self._load_from_string(f.read(), res.name)
                return
            except Exception as e:
                logger.warning(f"Failed to load built-in workflows: {e}")
                return

        for p in sorted(self._dir.glob("*.json")):
            try:
                self._load_from_string(p.read_text(encoding="utf-8"), str(p))
            except Exception as e:
                logger.exception("Error loading intent from %s: %s", p, e)

    def _load_from_string(self, json_str: str, source_name: str) -> None:
        """Helper to parse intent JSON."""
        try:
            raw = json.loads(json_str)

            # Support both single intent object and list of intents format
            items = [raw] if "id" in raw else raw.get("intents", [])

            for item in items:
                input_schema = item.get("input_schema", {"type": "object", "properties": {}})
                slots = input_schema.get("properties", {})
                intent = IntentDefinition(
                    id=item["id"],
                    title=item.get("title", item.get("name", item["id"])),
                    description=item.get("description", ""),
                    slots=slots,
                    input_schema=input_schema,
                    examples=item.get("examples", []),
                    workflow=item if "steps" in item else item.get("workflow", {}),
                )
                self._intents[intent.id] = intent
        except Exception as e:
            logger.exception("Error loading intent from %s: %s", source_name, e)

    def list(self) -> list[IntentDefinition]:
        return list(self._intents.values())

    def get(self, intent_id: str) -> IntentDefinition | None:
        return self._intents.get(intent_id)
