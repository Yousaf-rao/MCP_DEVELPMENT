import os
import json
import hashlib
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger("RouterCache")

CACHE_FILE = Path("router_cache.json")

class RouterCache:
    def __init__(self):
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load router cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save router cache: {e}")

    def _generate_key(self, node_id: str) -> str:
        """
        Uses the Node ID as the stable key.
        """
        return node_id

    def get(self, node_id: str) -> Optional[str]:
        if node_id in self.cache:
            path = self.cache[node_id]
            logger.info(f"⚡ Cache Hit: '{node_id}' -> {path}")
            return path
        return None

    def set(self, node_id: str, path: str):
        self.cache[node_id] = path
        self._save_cache()
