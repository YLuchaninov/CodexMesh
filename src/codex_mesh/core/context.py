"""
Application Context.
Holds global services and configuration for dependency injection.
"""

from dataclasses import dataclass

from ..config import CodexMeshConfig
from .events import EventBus


@dataclass
class AppContext:
    config: CodexMeshConfig
    event_bus: EventBus
