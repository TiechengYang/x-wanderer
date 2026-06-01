from typing import Dict, Any, Optional, List
import json
from datetime import datetime
from pathlib import Path
import sqlite3


class ProfileStore:
    """
    长期人物画像 + 话题画像存储（强化主动维护版）
    """
    def __init__(self, db_path: str = "data/sqlite/profiles.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                type TEXT,
                name TEXT,
                summary TEXT,
                key_insights TEXT,
                interaction_count INTEGER DEFAULT 0,
                last_updated TEXT,
                importance_score REAL DEFAULT 0.5,
                last_revisit TEXT
            )
        """)
        # 关系总结表（支持结构化图谱）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS relationship_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT,
                summary TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()
        # 轻量迁移：确保 last_revisit 列存在
        try:
            self.conn.execute("ALTER TABLE profiles ADD COLUMN last_revisit TEXT")
            self.conn.commit()
        except:
            pass

    def upsert_profile(self, profile_type: str, name: str, summary: str, 
                       key_insights: List[str], interaction_count: int = 1,
                       importance_score: float = None):
        profile_id = f"{profile_type}:{name}"
        insights_json = json.dumps(key_insights, ensure_ascii=False)

        existing = self.get_profile(profile_type, name)
        if existing and importance_score is None:
            importance_score = min(1.0, existing.get("importance_score", 0.5) + 0.08)

        self.conn.execute("""
            INSERT INTO profiles (id, type, name, summary, key_insights, interaction_count, last_updated, importance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                summary = excluded.summary,
                key_insights = excluded.key_insights,
                interaction_count = profiles.interaction_count + excluded.interaction_count,
                last_updated = excluded.last_updated,
                importance_score = COALESCE(excluded.importance_score, profiles.importance_score + 0.05)
        """, (profile_id, profile_type, name, summary, insights_json, interaction_count, 
              datetime.now().isoformat(), importance_score or 0.5))
        self.conn.commit()

    def get_profile(self, profile_type: str, name: str) -> Optional[Dict]:
        profile_id = f"{profile_type}:{name}"
        row = self.conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def get_top_profiles(self, profile_type: str = None, limit: int = 12) -> List[Dict]:
        if profile_type:
            rows = self.conn.execute(
                "SELECT * FROM profiles WHERE type = ? ORDER BY importance_score DESC, interaction_count DESC LIMIT ?",
                (profile_type, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM profiles ORDER BY importance_score DESC, interaction_count DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_relevant_profiles(self, query: str, top_k: int = 8) -> List[Dict]:
        all_profiles = self.get_top_profiles(limit=40)
        query_lower = query.lower()
        matched = []
        for p in all_profiles:
            score = 0
            if query_lower in p["name"].lower():
                score += 3
            if query_lower in p["summary"].lower():
                score += 2
            if any(query_lower in insight.lower() for insight in p.get("key_insights", [])):
                score += 1
            if score > 0:
                matched.append((score, p))
        matched.sort(key=lambda x: (x[0], x[1]["importance_score"]), reverse=True)
        return [p for score, p in matched[:top_k]]

    def _row_to_dict(self, row):
        # 兼容不同列数（迁移后可能有 last_revisit）
        d = {
            "id": row[0],
            "type": row[1],
            "name": row[2],
            "summary": row[3],
            "key_insights": json.loads(row[4]) if row[4] else [],
            "interaction_count": row[5],
            "last_updated": row[6],
            "importance_score": row[7],
        }
        d["last_revisit"] = row[8] if len(row) > 8 else None
        return d

    def record_revisit(self, profile_type: str, name: str):
        """记录回访时间，用于 suggest_profiles_to_revisit 降权"""
        profile_id = f"{profile_type}:{name}"
        now = datetime.now().isoformat()
        self.conn.execute(
            "UPDATE profiles SET last_revisit = ? WHERE id = ?",
            (now, profile_id)
        )
        self.conn.commit()

    def add_relationship_summary(self, target: str, summary: str):
        self.conn.execute(
            "INSERT INTO relationship_summaries (target, summary, timestamp) VALUES (?, ?, ?)",
            (target, summary, datetime.now().isoformat())
        )
        self.conn.commit()

    def get_recent_relationship_summaries(self, target: str = None, limit: int = 8) -> List[str]:
        if target:
            rows = self.conn.execute(
                "SELECT summary FROM relationship_summaries WHERE target = ? ORDER BY timestamp DESC LIMIT ?",
                (target, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT summary FROM relationship_summaries ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [r[0] for r in rows]
