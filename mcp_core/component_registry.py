import json
import os
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ComponentRegistry:
    def __init__(self, registry_path: str = "component_registry.json"):
        self.registry_path = registry_path
        self.mappings: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.registry_path):
            logger.info(f"Registry not found at {self.registry_path}, starting empty.")
            self.mappings = []
            return
        
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                self.mappings = data.get("mappings", [])
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            self.mappings = []

    def save(self):
        data = {"version": "1.0", "mappings": self.mappings}
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def register_component(self, figma_name: str, component_name: str, path: str, props: Dict = None):
        """Register or update a component mapping."""
        props = props or {}
        
        # Check for existing mapping to update
        for m in self.mappings:
            if m["figma_name"].lower() == figma_name.lower():
                m["component"] = component_name
                m["path"] = path
                m["props"] = props
                self.save()
                return
        
        # Add new
        self.mappings.append({
            "figma_name": figma_name,
            "component": component_name,
            "path": path,
            "props": props
        })
        self.save()

    def find_match(self, node_name: str) -> Optional[Dict]:
        """Find a component match for a given Figma node name."""
        node_name_lower = node_name.lower()
        
        # Sort by length of figma_name desc to match specific first ("Primary Button" vs "Button")
        # This prevents "Button" matching "Primary Button" if both exist
        sorted_mappings = sorted(self.mappings, key=lambda x: len(x["figma_name"]), reverse=True)
        
        for m in sorted_mappings:
            if m["figma_name"].lower() in node_name_lower:
                return m
        return None
