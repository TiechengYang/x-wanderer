import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from agent.memory.models import MemoryEntry, MemoryType
from agent.memory.stores.long_term_store import LongTermStore
from agent.memory.stores.chroma_store import ChromaMemoryStore
from agent.memory.profile_store import ProfileStore


class MemoryManager:
    def __init__(self, chroma_dir: str = "data/chroma", sqlite_path: str = "data/sqlite/memory.db"):
        self.long_term = LongTermStore(db_path=sqlite_path)
        self.semantic = ChromaMemoryStore(persist_dir=chroma_dir)
        self.profiles = ProfileStore()

    # === 基础记忆操作 ===
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

    # === 强化版画像系统 ===
    def update_person_profile(self, username: str, summary: str, key_insights: List[str], importance_boost: float = 0.1):
        self.profiles.upsert_profile("person", username, summary, key_insights, importance_score=None)
        existing = self.profiles.get_profile("person", username)
        if existing:
            new_importance = min(1.0, existing.get("importance_score", 0.5) + importance_boost)
            self.profiles.upsert_profile("person", username, summary, key_insights, importance_score=new_importance)

    def update_topic_profile(self, topic: str, summary: str, key_insights: List[str], importance_boost: float = 0.08):
        self.profiles.upsert_profile("topic", topic, summary, key_insights, importance_score=None)

    def get_relevant_profiles_text(self, query: str, top_k: int = 6) -> str:
        profiles = self.profiles.get_relevant_profiles(query, top_k=top_k)
        if not profiles:
            return "暂无相关长期画像。"
        lines = []
        for p in profiles:
            insights = "; ".join(p["key_insights"][:3]) if p["key_insights"] else "暂无"
            lines.append(f"- 【{p['type']}】{p['name']}：{p['summary']}（印象：{insights}）")
        return "\n".join(lines)

    def get_important_profiles(self, limit: int = 8) -> List[Dict]:
        """获取当前最重要的画像，用于反思和主动回访"""
        return self.profiles.get_top_profiles(limit=limit)

    def suggest_profiles_to_revisit(self, limit: int = 5) -> List[Dict]:
        """
        主动建议需要“回访”的重要画像
        策略：重要性高 + 最近互动较少（简化版）
        """
        all_important = self.profiles.get_top_profiles(limit=20)
        # 简单启发式：按重要性排序，优先推荐
        return sorted(all_important, key=lambda x: x["importance_score"], reverse=True)[:limit]

    # === 高级记忆压缩（支持主动画像维护） ===
    def compress_old_memories(self, llm, max_keep: int = 35):
        old_memories = self.long_term.get_recent_memories(limit=150)
        if len(old_memories) <= max_keep:
            return

        to_compress = old_memories[max_keep:]
        contents = "\n".join([m.content[:180] for m in to_compress[:25]])

        prompt = f"""
以下是过去一段时间的记忆片段，请完成：

1. 用 2-3 句话总结这段时期最核心的观察和模式。
2. 主动提取值得长期跟踪的重要人物和话题，并为每个生成简短画像（包括关键印象）。

记忆内容：
{contents}

输出格式：
总结：
[总结]

画像：
- [人物/话题名]：[描述 + 关键印象]
"""

        try:
            response = llm.invoke(prompt).content.strip()
            self.add_reflection(response, metadata={"type": "advanced_compression"})

            if "画像：" in response:
                lines = response.split("画像：")[-1].strip().split("\n")
                for line in lines:
                    if "：" in line:
                        try:
                            name_part, desc = line.split("：", 1)
                            name = name_part.strip("- ").strip()
                            if name:
                                ptype = "person" if "人物" in line.lower() else "topic"
                                self.profiles.upsert_profile(ptype, name, desc.strip()[:350], [], importance_score=0.65)
                        except:
                            pass

            print(f"[Memory] 高级压缩 + 主动画像维护完成，处理了 {len(to_compress)} 条记忆")
        except Exception as e:
            print(f"[Memory Compression Error] {e}")
