from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    REFLECTION = "reflection"
    RELATIONSHIP_SUMMARY = "relationship_summary"  # 新增：结构化关系总结


class MemoryEntry(BaseModel):
    id: str
    timestamp: datetime
    type: MemoryType
    content: str
    summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProfileType(str, Enum):
    PERSON = "person"
    TOPIC = "topic"


class Profile(BaseModel):
    id: str
    type: ProfileType
    name: str
    summary: str
    key_insights: List[str] = Field(default_factory=list)
    interaction_count: int = 0
    last_interaction: Optional[datetime] = None
    importance_score: float = 0.5
    relationship_strength: float = 0.3   # 关系强度
    last_revisit: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)  # 用于存放结构化关系总结片段
