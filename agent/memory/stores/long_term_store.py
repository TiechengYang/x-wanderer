import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from agent.memory.models import MemoryEntry, MemoryType


class LongTermStore:
    def __init__(self, db_path: str = "data/sqlite/memory.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                type TEXT,
                content TEXT,
                summary TEXT,
                metadata TEXT
            )
        """)
        self.conn.commit()

    def add_memory(self, entry: MemoryEntry):
        self.conn.execute("""
            INSERT OR REPLACE INTO memories (id, timestamp, type, content, summary, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.timestamp.isoformat(),
            entry.type.value,
            entry.content,
            entry.summary,
            json.dumps(entry.metadata)
        ))
        self.conn.commit()

    def get_recent_memories(self, limit: int = 50, memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        query = "SELECT * FROM memories"
        params = []
        if memory_type:
            query += " WHERE type = ?"
            params.append(memory_type.value)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(query, params).fetchall()
        return self._rows_to_entries(rows)

    def _rows_to_entries(self, rows) -> List[MemoryEntry]:
        entries = []
        for row in rows:
            entries.append(MemoryEntry(
                id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                type=MemoryType(row[2]),
                content=row[3],
                summary=row[4],
                metadata=json.loads(row[5]) if row[5] else {}
            ))
        return entries
