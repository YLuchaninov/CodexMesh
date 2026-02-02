"""
Plugin loader for CodexMesh.
"""

from __future__ import annotations

import importlib
import logging

from ..config import CodexMeshConfig
from ..extractors.registry import ExtractorRegistry

logger = logging.getLogger(__name__)


def load_skills(config: CodexMeshConfig, registry: ExtractorRegistry) -> None:
    """
    Each skill is a python module path. Convention:
      module must expose: def register(registry: ExtractorRegistry) -> None
    """
    for mod_name in config.skills:
        try:
            mod = importlib.import_module(mod_name)
            register = getattr(mod, "register", None)
            if callable(register):
                register(registry)
        except ImportError as e:
            # We log but don't crash if an optional skill fails to load
            logger.warning("Failed to load skill %s: %s", mod_name, e)
