# ADR 008: Semantic Merging & A11y 🧬

## Context
Code generation currently overwrites files completely. This prevents developers from manually enhancing the code (e.g., adding `useEffect`, `useRef`, or custom handlers). Additionally, accessibility (A11y) is currently limited to basic tags.

## Decision 1: Zone-Based Merging
We will implement a "Zone Marking" strategy for merging generated code with existing code.
- **Markers**: `{/* @mcp-begin:view */}` and `{/* @mcp-end:view */}`.
- **Logic**: 
    1. `generate_react_code` reads the target file if it exists.
    2. It scans for the "Generated Zone" (the JSX return block).
    3. It replaces ONLY the content between markers with the new Figma JSX.
    4. Code *outside* the markers (imports, state definitions, hooks) is preserved.
- **Fallback**: If no markers are found, it defaults to a full overwrite (or prompts context).

## Decision 2: Context-Aware A11y
We will expand `figma.py` to extract:
1. **Description -> aria-label**: Use the Figma layer description field.
2. **Interactive Roles**: Apply `role="button"` and `tabIndex={0}` to frames with `transitionNodeID` (prototype interactions) that are not native buttons.
3. **Heading Hierarchy**: Heuristic tracking of H1->H2->H3 based on text styles or layer names to ensure document outline validity.

## Consequences
- **Positive**: Enables "Hybrid" development (AI Gen + Manual Code). Improves SEO/A11y compliance.
- **Negative**: Requires developers to respect the zone markers; deleting them breaks the merger.
