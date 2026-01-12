from typing import Set

class StyleMerger:
    @staticmethod
    def reconcile_classes(existing_classes: str, incoming_classes: str) -> str:
        """
        Merge incoming Figma classes with existing developer classes.
        
        Strategy:
        1. Parse both strings into sets.
        2. Identify "Developer Protected" classes in existing set:
           - Interactive states: hover:, focus:, active:, disabled:
           - Responsive overrides: sm:, md:, lg:, xl:, 2xl: (Wait, design might dictate this?)
             -> Decision: Figma usually dictates layout. Dev overrides might be specific logic.
             -> Let's protect generic prefixes for now: hover, focus, dark, group, data.
           - Custom logic: data-*, aria-* (though aria usually props)
        3. Result = Incoming Set U Protected Developer Classes
        """
        if not existing_classes:
            return incoming_classes
            
        existing_set = set(existing_classes.split())
        incoming_set = set(incoming_classes.split())
        
        protected_prefixes = (
            "hover:", "focus:", "active:", "disabled:", "visited:",
            "group-", "peer-", "dark:", "data-", 
            "motion-", "animate-" # Dev might add custom animations
        )
        
        # Identify protected classes
        protected_classes = {
            c for c in existing_set 
            if any(c.startswith(p) for p in protected_prefixes)
            or c.startswith("wp-") # Example of project specific?
            or "[" in c and "]" in c # Arbitrary values might be dev specific? Or Figma? 
            # Figma generates arbitrary values too. Let's stick to state prefixes for safety.
        }
        
        # Merge
        # Note: We prioritize incoming structural/visual classes (bg, p, m, flex)
        # But we keep dev states.
        
        final_set = incoming_set.union(protected_classes)
        
        # Sort for deterministic output (nice for diffs)
        # Custom sorting: layout -> spacing -> visual -> interactive
        return " ".join(sorted(final_set))
