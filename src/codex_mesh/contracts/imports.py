"""
Import Contract definitions.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ImportKind(str, Enum):
    IMPORT = "import"
    FROM = "from"
    REQUIRE = "require"
    USING = "using"
    INCLUDE = "include"
    USE = "use"


class ImportContract(BaseModel):
    """
    Formal contract for an import statement.
    Used for validation and DevTools.
    """

    raw: str = Field(..., description="Raw import string")
    kind: ImportKind | str = Field(..., description="Import kind")
    candidates: list[str] = Field(default_factory=list, description="Resolved file candidates")
    is_external: bool = Field(False, description="Is external/stdlib")
    imported_names: list[str] | None = Field(None, description="Specific imported symbols")
    alias_map: dict[str, str] | None = Field(None, description="Alias mapping")
    is_star: bool = Field(False, description="Is wildcard import")
