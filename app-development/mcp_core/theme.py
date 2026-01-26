from typing import Dict, Any, Tuple
import math

class DesignTokenMapper:
    """Methods to map raw Figma values to Tailwind design tokens."""
    
    # Default Color Palette (Tailwind-ish)
    THEME_COLORS = {
        # Slate
        "#f8fafc": "slate-50", "#f1f5f9": "slate-100", "#e2e8f0": "slate-200",
        "#cbd5e1": "slate-300", "#94a3b8": "slate-400", "#64748b": "slate-500",
        "#475569": "slate-600", "#334155": "slate-700", "#1e293b": "slate-800",
        "#0f172a": "slate-900",
        # Blue
        "#eff6ff": "blue-50", "#dbeafe": "blue-100", "#bfdbfe": "blue-200",
        "#93c5fd": "blue-300", "#60a5fa": "blue-400", "#3b82f6": "blue-500",
        "#2563eb": "blue-600", "#1d4ed8": "blue-700", "#1e40af": "blue-800",
        "#1e3a8a": "blue-900",
        # Red
        "#fef2f2": "red-50", "#fee2e2": "red-100", "#fecaca": "red-200",
        "#fca5a5": "red-300", "#f87171": "red-400", "#ef4444": "red-500",
        "#dc2626": "red-600", "#b91c1c": "red-700", "#991b1b": "red-800",
        "#7f1d1d": "red-900",
        # Green
        "#f0fdf4": "green-50", "#dcfce7": "green-100", "#bbf7d0": "green-200",
        "#86efac": "green-300", "#4ade80": "green-400", "#22c55e": "green-500",
        "#16a34a": "green-600", "#15803d": "green-700", "#166534": "green-800",
        "#14532d": "green-900",
        # White/Black
        "#ffffff": "white", "#000000": "black"
    }

    @staticmethod
    def _hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
        hex_code = hex_code.lstrip("#")
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _color_distance(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> float:
        """Euclidean distance between two RGB colors."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))

    @classmethod
    def map_color(cls, hex_code: str, threshold: float = 30.0) -> str:
        """
        Map a hex code to the nearest Tailwind class.
        returns: "bg-blue-500" format expected? No, just "blue-500".
        Tool consuming this should prepend bg- or text-.
        If no close match found, returns None.
        """
        try:
            target_rgb = cls._hex_to_rgb(hex_code)
        except ValueError:
            return None # Invalid hex

        best_match = None
        min_dist = float("inf")

        for theme_hex, theme_name in cls.THEME_COLORS.items():
            theme_rgb = cls._hex_to_rgb(theme_hex)
            dist = cls._color_distance(target_rgb, theme_rgb)
            
            if dist < min_dist:
                min_dist = dist
                best_match = theme_name
        
        # Threshold check (approximation allowance)
        # 30.0 is roughly 10-12% difference
        if min_dist <= threshold:
            return best_match
            
        return None

    @staticmethod
    def map_spacing(px: float) -> str:
        """
        Map pixels to Tailwind spacing scale (1 unit = 4px).
        e.g., 16px -> "4" (p-4), 24px -> "6" (p-6).
        Returns None if no clean mapping (e.g. 17px).
        Allows small float deviations (e.g. 15.9 -> 16).
        """
        if px <= 0: return "0"
        
        # Round to nearest pixel first
        pixel_val = round(px)
        
        # Check standard Tailwind logic (divisible by 4 is standard)
        if pixel_val % 4 == 0:
            return str(pixel_val // 4)
        
        # Specific updates for 0.5, 1.5 etc?
        # 2px -> 0.5
        if pixel_val == 2: return "0.5"
        # 6px -> 1.5
        if pixel_val == 6: return "1.5"
        # 10px -> 2.5
        if pixel_val == 10: return "2.5"
        
        # If very close to 4n, snap to it?
        # (Already rounded above)
        
        return None
