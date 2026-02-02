"""Edge type definitions for the code graph."""

from enum import Enum

from pydantic import BaseModel, Field


class EdgeType(str, Enum):
    """Types of edges (relationships) in the code graph."""

    CONTAINS = "contains"  # File -> Symbol / File -> Query
    IMPORTS = "imports"  # File -> File/Module
    CALLS = "calls"  # Function -> Function
    INHERITS = "inherits"  # Class -> Class
    REFERENCES = "references"  # Any -> Any (type usage, variable reference)
    READS = "reads"  # Query -> Table
    WRITES = "writes"  # Query -> Table
    DOCUMENTS = "documents"  # Doc -> Symbol
    DOCUMENTED_BY = "documented_by"  # Symbol -> Doc


EDGE_WEIGHTS: dict[EdgeType, float] = {
    EdgeType.CONTAINS: 1.0,
    EdgeType.IMPORTS: 0.5,
    EdgeType.CALLS: 2.0,
    EdgeType.INHERITS: 1.5,
    EdgeType.REFERENCES: 0.8,
    EdgeType.READS: 1.2,
    EdgeType.WRITES: 1.6,
    EdgeType.DOCUMENTS: 1.0,
    EdgeType.DOCUMENTED_BY: 1.0,
}


class Edge(BaseModel):
    """Represents a directed edge in the code graph."""

    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    edge_type: EdgeType = Field(..., description="Type of relationship")
    weight: float = Field(1.0, description="Edge weight for ranking")
    metadata: dict | None = Field(None, description="Additional edge metadata")

    @classmethod
    def create(
        cls,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float | None = None,
        metadata: dict | None = None,
    ) -> "Edge":
        """Create an Edge with default weight based on type."""
        if weight is None:
            weight = EDGE_WEIGHTS.get(edge_type, 1.0)
        return cls(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            metadata=metadata,
        )
