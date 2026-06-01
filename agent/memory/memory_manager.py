import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from agent.memory.models import MemoryEntry, MemoryType, Profile, ProfileType
from agent.memory.stores.long_term_store import LongTermStore
from agent.memory.stores.chroma_store import ChromaMemoryStore
from agent.memory.profile_store import ProfileStore


class MemoryManager:
    def __init__(self, chroma_dir: str = "data/chroma", sqlite_path: str = "data/sqlite/memory.db"):
        self.long_term = LongTermStore(db_path=sqlite_path)
        self.semantic = ChromaMemoryStore(persist_dir=chroma_dir)
        self.profiles = ProfileStore()

    # === 基础记忆操作（保持原有逻辑） ===
    def add_episodic_memory(self, content: str, metadata: Dict[str, Any] = None):
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            type=MemoryType.EPISODIC,
            content=content,
            metadata=metadata or {}
        )
        self.long_term.add_memory(entry)
        self.semantic.add(entry.id, content, metadata)

    def add_reflection(self, content: str, metadata: Dict[str, Any] = None):
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            type=MemoryType.REFLECTION,
            content=content,
            metadata=metadata or {}
        )
        self.long_term.add_memory(entry)
        self.semantic.add(entry.id, content, {"type": "reflection", **(metadata or {})})

    def add_relationship_summary(self, target_name: str, summary: str, metadata: Dict[str, Any] = None):
        """新增：存储结构化的关系总结"""
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            type=MemoryType.RELATIONSHIP_SUMMARY,
            content=summary,
            metadata={"target": target_name, **(metadata or {})}
        )
        self.long_term.add_memory(entry)
        self.semantic.add(entry.id, summary, {"type": "relationship_summary", "target": target_name})

    # === 画像系统（强化主动性） ===
    def update_person_profile(self, username: str, summary: str, key_insights: List[str], importance_boost: float = 0.1):
        self.profiles.upsert_profile("person", username, summary, key_insights, importance_score=None)
        existing = self.profiles.get_profile("person", username)
        if existing:
            new_importance = min(1.0, existing.get("importance_score", 0.5) + importance_boost)
            self.profiles.upsert_profile("person", username, summary, key_insights, importance_score=new_importance)

    def update_topic_profile(self, topic: str, summary: str, key_insights: List[str], importance_boost: float = 0.08):
        self.profiles.upsert_profile("topic", topic, summary, key_insights, importance_score=None)

    def get_important_profiles(self, limit: int = 8) -> List[Dict]:
        return self.profiles.get_top_profiles(limit=limit)

    def suggest_profiles_to_revisit(self, limit: int = 5, days_since_last: int = 7) -> List[Dict]:
        """更主动的回访建议：优先推荐重要但很久没互动的画像"""
        all_profiles = self.profiles.get_top_profiles(limit=30)
        now = datetime.now()
        candidates = []

        for p in all_profiles:
            last = p.get("last_revisit") or p.get("last_updated")
            if last:
                try:
                    last_dt = datetime.fromisoformat(last)
                    days = (now - last_dt).days
                except:
                    days = 999
            else:
                days = 999

            if days >= days_since_last:
                score = p.get("importance_score", 0.5) * (1 + min(days / 30, 2))
                candidates.append((score, p))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in candidates[:limit]]

    def record_profile_revisit(self, profile_type: str, name: str):
        """记录一次回访行为"""
        self.profiles.upsert_profile(profile_type, name, "", [], importance_score=None)  # 触发更新 last_revisit

    # === 检索增强 ===
    def retrieve_relevant_memories(self, query: str, top_k: int = 8) -> List[str]:
        try:
            reflection_results = self.semantic.search(
                query, n_results=max(3, top_k // 2),
                filter_metadata={"type": "reflection"}
            )
            general_results = self.semantic.search(query, n_results=top_k)

            combined = []
            if reflection_results and reflection_results.get("documents"):
                for doc in reflection_results["documents"][0]:
                    combined.append(f"[反思] {doc}")

            if general_results and general_results.get("documents"):
                for doc in general_results["documents"][0][:top_k - len(combined)]:
                    combined.append(doc)
            return combined[:top_k]
        except Exception as e:
            print(f"[Memory Retrieval Error] {e}")
            return []

    def get_recent_relationship_summaries(self, target: str = None, limit: int = 5) -> List[str]:
        """获取针对特定目标或最近的关系总结"""
        # 简化实现：从长期存储中筛选
        memories = self.long_term.get_recent_memories(limit=50, memory_type=MemoryType.RELATIONSHIP_SUMMARY)
        results = []
        for m in memories:
            if target is None or m.metadata.get("target") == target:
                results.append(m.content)
            if len(results) >= limit:
                break
        return results

    # === 高级压缩（保持并增强） ===
    def compress_old_memories(self, llm, max_keep: int = 35):
        # ... (保留原有逻辑，可后续增强)
        pass
