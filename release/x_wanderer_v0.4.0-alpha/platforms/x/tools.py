from typing import List, Dict, Any
from platforms.x.client import XClient

_x_client = None

def get_x_client() -> XClient:
    global _x_client
    if _x_client is None:
        _x_client = XClient()
    return _x_client


def search_x(query: str, max_results: int = 8, since_id: str = None) -> List[Dict[str, Any]]:
    """供 wander / observe 使用的搜索工具"""
    client = get_x_client()
    return client.search_recent(query, max_results=max_results, since_id=since_id)


def post_on_x(text: str, reply_to: str = None) -> str | None:
    """在 X 上发言（必须带 AI 声明）"""
    client = get_x_client()
    # 强制添加 AI 身份声明（符合我们之前的设计）
    if "AI" not in text and "我是" not in text:
        text = text + "\n\n（我是AI助手，正在进行数字漫游）"
    return client.create_tweet(text, reply_to=reply_to)
