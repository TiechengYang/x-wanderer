from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    REFLECTION = "reflection"


class MemoryEntry(BaseModel):
    id: str
    timestamp: datetime
    type: MemoryType
    content: str
    summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
