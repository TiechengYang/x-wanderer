import uuid
from datetime import datetime, timedelta
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

    def add_relationship_summary(self, target_name: str, summary: str):
        """存储结构化关系总结（用于图谱和 supervisor 消费）"""
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            type=MemoryType.RELATIONSHIP_SUMMARY,
            content=summary,
            metadata={"target": target_name, "type": "relationship_summary"}
        )
        self.long_term.add_memory(entry)
        self.semantic.add(entry.id, f"[{target_name}] {summary}", {"type": "relationship_summary", "target": target_name})

    def get_recent_relationship_summaries(self, target: str = None, limit: int = 5) -> List[str]:
        memories = self.long_term.get_recent_memories(limit=50, memory_type=MemoryType.RELATIONSHIP_SUMMARY)
        results = []
        for m in memories:
            if target is None or m.metadata.get("target") == target:
                results.append(m.content)
            if len(results) >= limit:
                break
        return results

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

    # === 强化版画像系统（支持主动回访） ===
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
            lines.append(f"- 【{p['type']}】{p['name']}：{p['summary']}（印象：{insights}，重要性 {p.get('importance_score', 0):.2f}）")
        return "\n".join(lines)

    def get_important_profiles(self, limit: int = 8) -> List[Dict]:
        """获取当前最重要的画像，用于反思和主动回访"""
        return self.profiles.get_top_profiles(limit=limit)

    def suggest_profiles_to_revisit(self, limit: int = 5, days_since_last: int = 5) -> List[Dict]:
        """
        主动建议需要“回访”的重要画像
        策略：重要性高 + 最近互动/回访较少
        """
        all_important = self.profiles.get_top_profiles(limit=30)
        now = datetime.now()
        scored = []
        for p in all_important:
            last = p.get("last_revisit") or p.get("last_updated")
            days = 999
            if last:
                try:
                    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00")) if isinstance(last, str) else last
                    days = (now - last_dt).days
                except:
                    days = 30
            score = p.get("importance_score", 0.5) * 1.5 + max(0, days / 10.0)
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def record_profile_revisit(self, profile_type: str, name: str):
        """记录一次回访/互动，用于 suggest_profiles_to_revisit 降权"""
        self.profiles.record_revisit(profile_type, name)

    def seed_forced_revisit_targets(self, names: List[str], reason: str = "scheduler_nudge"):
        """
        调度器/外部系统可直接用此方法注入高价值回访目标。
        这些目标会被 supervisor 在下一次决策时以较高优先级合并进 active_revisit_targets。
        """
        if not names:
            return
        content = f"【强制回访种子】{reason}：{', '.join(names[:6])}"
        self.add_reflection(content, metadata={
            "type": "forced_revisit_seed",
            "targets": names[:8],
            "reason": reason
        })
        for n in names[:8]:
            try:
                self.profiles.upsert_profile("person", n, f"被调度器标记为高优先级（{reason}）", [], importance_score=0.88)
            except:
                pass
        print(f"[Memory] 已种子强制回访目标: {names[:5]}")

    # === 高级记忆压缩 ===
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

    # === 核心：激进版全局人物分析（ABC 重点） ===
    def analyze_all_people(self, llm, top_n: int = 20) -> Dict[str, Any]:
        """
        对所有积累的长期画像进行一次全局结构化分析。
        输出：
        - report: 详细的社交图谱洞见报告
        - high_priority_people: 必须立即主动回访的用户名列表（按优先级）
        - suggested_sub_goals: 高度具体的子目标建议
        - goal_adjustment_suggestion: 对当前主目标的强力调整建议
        """
        profiles = self.profiles.get_top_profiles(limit=top_n)
        if not profiles:
            return {
                "report": "目前还没有积累足够的人物画像，无法进行全局分析。",
                "high_priority_people": [],
                "suggested_sub_goals": [],
                "goal_adjustment_suggestion": None
            }

        profile_lines = []
        for p in profiles:
            insights = "; ".join(p.get("key_insights", [])[:3])
            profile_lines.append(
                f"- {p['name']} (类型:{p['type']}, 重要性:{p.get('importance_score',0):.2f}, 互动:{p.get('interaction_count',0)})\n  印象:{p.get('summary','')[:160]}\n  关键点:{insights}"
            )

        recent_summaries = self.get_recent_relationship_summaries(limit=8)
        summaries_text = "\n".join([f"• {s}" for s in recent_summaries]) if recent_summaries else "暂无结构化关系总结。"

        analysis_prompt = f"""
你是一个高度擅长长期社交关系建模与战略规划的 AI 分析引擎。

下面是当前积累的 {len(profiles)} 位重要人物/话题的长期画像，以及最近的关系总结：

【长期画像】
{chr(10).join(profile_lines)}

【最近结构化关系总结】
{summaries_text}

请完成以下高强度分析任务（输出必须是结构化的 JSON 风格文本）：

1. **整体关系图谱报告**（report）：
   - 谁是当前最有价值/最值得深度维护的核心节点？
   - 存在哪些明显的聚类或桥梁人物？
   - 哪些人目前被忽略但有高潜力？
   - 整体社交图谱的健康度与机会点。

2. **高优先级主动回访名单**（high_priority_people）：
   列出 3~7 个最应该在接下来 1-3 天内主动接触的用户名（只输出干净的用户名，不要 @ 或其他符号）。优先级从高到低排序。

3. **建议子目标**（suggested_sub_goals）：
   给出 2~4 个极度具体、可执行的子目标，格式类似：
   "与 @用户名 进行至少 2 轮深度对话，探索其对[具体话题]的看法，并记录 3 条新洞见"

4. **主目标调整建议**（goal_adjustment_suggestion）：
   一段 60-140 字的强力建议：当前主目标是否已经偏离实际积累的社会图谱？应该如何调整主目标方向，使其与高价值关系更紧密结合。

请严格按照以下格式输出（不要多余解释）：
REPORT:
[详细报告文本]

HIGH_PRIORITY:
username1, username2, ...

SUB_GOALS:
- 子目标1
- 子目标2

GOAL_ADJUST:
[调整建议文本]
"""

        report = ""
        high_priority = []
        suggested_sub_goals = []
        goal_adjustment = None

        try:
            if llm:
                resp = llm.invoke(analysis_prompt)
                raw = resp.content.strip()

                # 粗暴但有效的解析
                if "REPORT:" in raw:
                    report = raw.split("REPORT:")[1].split("HIGH_PRIORITY:")[0].strip()
                if "HIGH_PRIORITY:" in raw:
                    hp_raw = raw.split("HIGH_PRIORITY:")[1].split("SUB_GOALS:")[0].strip()
                    high_priority = [x.strip().lstrip("@") for x in hp_raw.replace("\n", ",").split(",") if x.strip() and len(x.strip()) > 1][:7]
                if "SUB_GOALS:" in raw:
                    sg_part = raw.split("SUB_GOALS:")[1].split("GOAL_ADJUST:")[0].strip()
                    suggested_sub_goals = [line.strip("- ").strip() for line in sg_part.split("\n") if line.strip()]
                if "GOAL_ADJUST:" in raw:
                    goal_adjustment = raw.split("GOAL_ADJUST:")[1].strip()[:400]
            else:
                report = "LLM 不可用时的模拟分析：当前积累了多位高潜力人物，建议优先回访核心桥梁节点。"
                high_priority = [p["name"] for p in profiles[:4]]
                suggested_sub_goals = [f"与 {p['name']} 进行深度多轮互动并提取洞见" for p in profiles[:2]]
                goal_adjustment = "当前主目标与实际积累的高价值社会关系脱节，建议把主目标调整为围绕 3-5 位核心人物进行长期关系维护与知识萃取。"
        except Exception as e:
            print(f"[AnalyzeAllPeople LLM Error] {e}")
            report = f"分析过程中出错: {str(e)[:120]}"
            high_priority = [p["name"] for p in profiles[:3]]

        # 额外：为高优先级人物提升重要性
        for name in high_priority[:5]:
            try:
                self.profiles.upsert_profile("person", name, f"被全局分析标记为高优先级回访对象", [], importance_score=0.92)
            except:
                pass

        print(f"[MemoryManager] 全局人物分析完成。高优先级回访目标: {high_priority[:5]}")

        return {
            "report": report[:2200],
            "high_priority_people": high_priority,
            "suggested_sub_goals": suggested_sub_goals[:5],
            "goal_adjustment_suggestion": goal_adjustment
        }

    # === 更丰富的结构化关系图谱（供 supervisor 直接消费） ===
    def generate_relationship_graph_structured(self, top_n: int = 12) -> dict:
        """
        返回极致丰富的结构化人物关系图谱，包含节点、强类型边、强度、聚类、洞见
        供 supervisor 直接在 prompt 中使用，驱动更激进的关系维护决策。
        """
        all_people = self.profiles.get_top_profiles(profile_type="person", limit=top_n)
        if not all_people:
            return {"nodes": [], "edges": [], "clusters": [], "insights": [], "generated_at": datetime.now().isoformat()}

        nodes = []
        edges = []
        name_to_profile = {p["name"]: p for p in all_people}

        for p in all_people:
            nodes.append({
                "name": p["name"],
                "type": "person",
                "importance": round(p.get("importance_score", 0), 2),
                "interactions": p.get("interaction_count", 0),
                "relationship_strength": round(p.get("relationship_strength", 0.3), 2),
                "last_revisit": p.get("last_revisit"),
                "summary": (p.get("summary", "") or "")[:160]
            })

        # 使用关系总结构建更真实的边
        clusters = {}
        for p in all_people:
            summaries = self.get_recent_relationship_summaries(target=p["name"], limit=6)
            connected = set()

            for s in summaries:
                for other_name in name_to_profile:
                    if other_name != p["name"] and other_name.lower() in s.lower():
                        connected.add(other_name)
                        edge_type = "mentioned_together"
                        if any(k in s for k in ["共同", "一起", "合作", "和", "与"]):
                            edge_type = "co_engagement"
                        elif any(k in s for k in ["回复", "互动", "对话", "讨论"]):
                            edge_type = "direct_interaction"
                        strength = 0.85 if edge_type == "co_engagement" else (0.7 if edge_type == "direct_interaction" else 0.5)
                        edges.append({
                            "source": p["name"],
                            "target": other_name,
                            "type": edge_type,
                            "strength": round(strength, 2)
                        })

            if connected:
                ck = tuple(sorted(list(connected))[:3])
                if ck not in clusters:
                    clusters[ck] = []
                clusters[ck].append(p["name"])

        # 高级洞见
        insights = []
        high_imp = sorted(nodes, key=lambda n: n["importance"], reverse=True)[:4]
        if high_imp:
            insights.append(f"核心高价值节点：{', '.join([n['name'] for n in high_imp])}")

        bridge = []
        for p in all_people:
            summaries = self.get_recent_relationship_summaries(target=p["name"], limit=5)
            connected = set()
            for s in summaries:
                for other in name_to_profile:
                    if other != p["name"] and other.lower() in s.lower():
                        connected.add(other)
            if len(connected) >= 2:
                bridge.append((p["name"], len(connected)))
        if bridge:
            bridge.sort(key=lambda x: -x[1])
            insights.append(f"关键桥梁人物：{bridge[0][0]}（连接 {bridge[0][1]} 个其他重要节点）")

        # 冷门高潜力
        cold_high = [n for n in nodes if n["importance"] > 0.65 and n["interactions"] < 4]
        if cold_high:
            insights.append(f"被低估的高潜力对象：{', '.join([n['name'] for n in cold_high[:3]])} — 值得发起新接触")

        return {
            "nodes": nodes,
            "edges": edges[:50],
            "clusters": [{"members": list(m)} for m in clusters.values() if len(m) >= 2],
            "insights": insights,
            "generated_at": datetime.now().isoformat()
        }
