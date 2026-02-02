"""
CodexMesh Extractors module.

Contains language/domain extractors + registry.

Per architecture.md: Language-specific or domain-specific data extractors.
"""

from .protocols import ExtractionResult, Extractor, ExtractorContext, PendingCall, PendingImport
from .registry import ExtractorRegistry

__all__ = [
    "Extractor",
    "ExtractorContext",
    "ExtractionResult",
    "PendingCall",
    "PendingImport",
    "ExtractorRegistry",
]
