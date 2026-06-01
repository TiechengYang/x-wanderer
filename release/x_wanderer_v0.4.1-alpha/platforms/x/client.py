import tweepy
import time
import logging
from typing import List, Dict, Any, Optional
from config.settings import get_settings

settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("XClient")


class XClient:
    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=settings.x_bearer_token,
            consumer_key=settings.x_api_key,
            consumer_secret=settings.x_api_secret,
            access_token=settings.x_access_token,
            access_token_secret=settings.x_access_secret,
            wait_on_rate_limit=True
        )
        self.last_request_time = 0
        self.min_interval = 1.5

    def _safe_request(self, func, *args, **kwargs):
        """带重试和限流保护的请求包装器"""
        for attempt in range(3):
            self._rate_limit_protect()
            try:
                return func(*args, **kwargs)
            except tweepy.TooManyRequests:
                wait = 60 * (attempt + 1)
                logger.warning(f"触发 X API 速率限制，等待 {wait} 秒后重试...")
                time.sleep(wait)
            except Exception as e:
                logger.error(f"X API 调用失败 (尝试 {attempt+1}/3): {e}")
                if attempt == 2:
                    return None
                time.sleep(5)
        return None

    def _rate_limit_protect(self):
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def search_recent(self, query: str, max_results: int = 10, since_id: Optional[str] = None) -> List[Dict[str, Any]]:
        def _do_search():
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                since_id=since_id,
                tweet_fields=["created_at", "author_id", "public_metrics", "text"],
                user_fields=["username", "name"],
                expansions=["author_id"]
            )
            results = []
            if tweets.data:
                users = {u.id: u for u in tweets.includes.get("users", [])}
                for tweet in tweets.data:
                    user = users.get(tweet.author_id)
                    results.append({
                        "id": str(tweet.id),
                        "text": tweet.text,
                        "created_at": tweet.created_at,
                        "author_id": str(tweet.author_id),
                        "author_username": user.username if user else None,
                        "public_metrics": tweet.public_metrics or {},
                    })
            return results

        return self._safe_request(_do_search) or []

    def create_tweet(self, text: str, reply_to: Optional[str] = None) -> Optional[str]:
        def _do_post():
            if reply_to:
                resp = self.client.create_tweet(text=text, in_reply_to_tweet_id=reply_to)
            else:
                resp = self.client.create_tweet(text=text)
            return str(resp.data["id"])

        return self._safe_request(_do_post)
