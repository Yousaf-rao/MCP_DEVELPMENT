# ADR 009: Advanced Semantic Engine 🧠

## Context
Standard overwriting or simple text merging is insufficient for "Hybrid" components where developers mix AI-generated structure with manual business logic. We need a "Logic-Aware" engine.

## Decision 1: Tailwind Diffing (Set-Based)
Instead of replacing `className` strings entirely, we will perform a Set Difference:
- **New Classes**: Derived from Figma (e.g., `bg-blue-500`, `p-4`).
- **Existing Classes**: Extracted from current code (e.g., `bg-red-500`, `hover:scale-105`).
- **Logic**: 
    1. Identify conflicting utility categories (e.g., `bg-` cannot have both blue and red).
    2. Overwrite conflicting style classes with Figma's version.
    3. **Preserve** non-conflicting manual classes (e.g., `hover:` states, `data-` attributes).

## Decision 2: Refactoring Awareness
Use `ComponentRegistry` to find the *actual* file path of a component before regenerating it.
- If `UserProfile` was moved to `src/features/user/UserProfile.tsx`, the engine must update it *there*, not recreate it in the default output directory.

## Decision 3: Prop Patching (Regex/AST)
For "Smart Components" (`<Button />`), the engine will:
- Update visual props: `variant`, `size`, `className`.
- **Preserve** logic props: `onClick`, `disabled` (if manually set), `ref`.

## Implementation
- **Tools**: Enhance `CodeMerger` with regex-based attribute parsing (until AST parser is integrated).
- **Workflow**: `generate_react_code` -> `registry.find_path()` -> `CodeMerger.patch_attributes()`.

## Consequences
- **Positive**: "Zero-Touch" updates become safe for complex components.
- **Negative**: Regex patching is fragile; requires strict code formatting until AST is available.
