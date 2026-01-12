# ADR 001: LLM-First Architecture

## Status
Accepted

## Context
The previous system relied on a `component_registry.json` and strict rule-based logic to map Figma nodes to React components. This approach was brittle, required manual maintenance of the registry, and failed to handle novel or complex designs.

## Decision
We have replaced the rule-based engine with an **LLM-First Architecture** powered by **Google Gemini 1.5 Flash**.

The new `LLMCoder` service:
1.  Accepts raw Figma JSON data.
2.  Accepts project context (e.g., `tailwind.config.js`).
3.  Generates production-ready React/TypeScript code dynamically.

## Consequences
### Positive
*   **Flexibility:** Can generate code for *any* design, not just registered components.
*   **Zero Config:** No need to manually map "Button" -> "Button.tsx".
*   **Context Aware:** Can adapt to different design systems (Tailwind, MUI) via profiles.

### Negative
*   **Non-Deterministic:** Output may vary slightly between runs (mitigated by Router Cache).
*   **Cost:** Incurs API costs per generation (mitigated by Router Cache).
