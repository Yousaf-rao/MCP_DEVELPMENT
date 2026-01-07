# ADR 006: 2026 Production Architecture

## Status
Accepted

## Context
The initial Figma automation tools were built for specific, small-scale tasks ("sprint 1"). As we move to production ("2026 vision"), we need to address scalability, maintainability, and design system integration.
Key pain points:
1.  **Blocking I/O**: `requests` library halts execution.
2.  **Hardcoded Values**: Hex codes and pixels make code unmaintainable.
3.  **Dumb Components**: Outputting raw `div` tags ignores the project's React component library.
4.  **Asset Bottlenecks**: Manual asset handling doesn't scale.

## Decision
We will refactor the system into four pillars:

### 1. Core Performance (Async & Math)
-   **Adoption**: `httpx` for true non-blocking I/O.
-   **Logic**: `BoundingBox` calculator validation to determine relative layout coordinates (`child.abs - parent.abs`) instead of relying on global or simple offsets.

### 2. Intelligent Design (Tokens)
-   **Token Mapper**: A `DesignTokenMapper` class will translate raw Figma values to `theme.json` or Tailwind classes.
    -   `#3b82f6` -> `blue-500`
    -   `16px` -> `p-4`
-   **Fuzzy Matching**: Logic to handle sub-pixel imperfections (e.g., `15.8px` -> `16px`).

### 3. Smart Components (Pattern Recognition)
-   **Overrides**: A configuration map `{"LayerName": "<ComponentName />"}`.
-   **Interactions**: Detect Figma Prototype triggers to auto-add `onClick` handlers.
-   **Accessibility**: Auto-generate `aria-label` from layer names.

### 4. Modern Architecture (Assets & Events)
-   **Asset Pipeline**: Automated fetching of image binaries -> S3/Cloud Storage -> CDN URL.
-   **Event Bus**: Abstracting `EventStore` to support Redis/Queueing systems for horizontal scaling.

## Consequences
-   **Complexity**: Higher initial setup (need theme mapping, mock S3, etc.).
-   **Dependencies**: Added `httpx`.
-   **Maintainability**: Significantly improved. Generated code will look hand-written and adhere to the project's design system.
