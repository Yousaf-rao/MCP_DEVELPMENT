# ADR 010: AST-Based Semantic Merging 🧠

## Context
Our current `CodeMerger` relies on Regex and "Zone Markers" (`{/* @mcp-begin:view */}`). This is fragile, requires manual developer compliance, and cannot safely merge granular props or preserve hooks without strict markers. The user requires a "Markerless" and "Logic-Agnostic" approach.

## Decision: Adopt Abstract Syntax Tree (AST) Parsing
We will upgrade the engine to parse the codebase into an AST before applying updates.

### 1. Parser Strategy
We will implement an **AST Bridge**.
- **Preferred**: `LibCST` (Python) if sufficient for TSX, or `tree-sitter` (Python bindings).
- **Fallback**: A lightweight Node.js sidecar (`mcp-parser-service`) using `@babel/parser` if Python tooling is insufficient for complex TSX.
- *Rationale*: AST allows us to identify nodes (`ExportNamedDeclaration`, `ReturnStatement`, `CallExpression`) with 100% confidence.

### 2. Implementation Logic
1.  **Parse**: Load `.tsx` into AST.
2.  **Traverse**: Locate the target component by Name.
3.  **Fingerprint**: Identify the "Logic Block" (Hooks, State) vs the "Render Block" (Return statement).
4.  **Diff & Patch**:
    *   **Props**: Iterate JSX attributes. If attribute exists in Figma (e.g., `className`), update it. If unrelated (e.g., `onClick`), preserve it.
    *   **Structure**: If the wrapper changes (e.g., `<div>` -> `<section>`), wrap the inner content while preserving key children.
5.  **Generate**: Serialize AST back to code (preserving comments and formatting).

## Consequences
- **Positive**: "Markerless" merging (no more `{/* @mcp */}`). Safer updates. Refactoring resilience.
- **Negative**: Higher complexity. Potential dependency on Node.js or compiled Python extensions. Slower performance than Regex.
