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
        """Backwards compatible get (returns path only)."""
        entry = self.cache.get(node_id)
        if isinstance(entry, dict) and "path" in entry:
            logger.info(f"⚡ Cache Hit: '{node_id}' -> {entry['path']}")
            return entry["path"]
        # Legacy support if cache has string
        if isinstance(entry, str):
            return entry
        return None

    def get_entry(self, node_id: str) -> Optional[dict]:
        """Returns full cache entry with metadata."""
        return self.cache.get(node_id)

    def set(self, node_id: str, path: str, last_modified: str = None):
        self.cache[node_id] = {
            "path": path,
            "last_modified": last_modified
        }
        self._save_cache()
