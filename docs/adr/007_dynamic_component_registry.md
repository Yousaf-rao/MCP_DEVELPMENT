# ADR 007: Dynamic Component Registry & Discovery 🧠

## Context
Refactoring the `Figma-to-React` engine from hardcoded "Smart Components" to a configuration-driven system that scales with the user's codebase.

## Decision
We will implement a 3-part system:
1.  **Component Registry (`component_registry.json`)**: A centralized JSON file defining mappings between Figma layers and React components, including prop translation rules.
2.  **Discovery Tool**: A new MCP tool (`figma.scan_components`) that analyzes the repo to auto-populate the registry.
3.  **Dynamic Rendering**: Update `figma.py` to load this registry at runtime instead of using a hardcoded `COMPONENT_MAP`.

## Schema: `component_registry.json`
```json
{
  "mappings": [
    {
      "figma_name": "Primary Button",
      "component": "Button",
      "path": "@/components/ui/button",
      "props": {
        "variant": "primary",
        "size": "default"
      }
    },
    {
      "figma_name": "Input Field",
      "component": "Input",
      "path": "@/components/ui/input"
    }
  ],
  "version": "1.0"
}
```

## Discovery Logic
- Scan `src/components` or `components/` for `.tsx` files.
- Parse exports to find component names.
- Heuristic matching: Component Name "UserProfile" <-> Figma Layer "User Profile".

## Consequences
- **Positive**: Decouples logic from configuration. allows project-specific customization without code changes.
- **Negative**: Requires strict naming conventions or manual tuning of the JSON map if heuristics fail.
