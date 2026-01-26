# ADR 002: Hybrid Vision Strategy

## Status
Accepted

## Context
Standard LLM generation based solely on Figma's JSON data often fails to capture the "gestalt" or layout of a component. Nested Frames in Figma can be messy, leading to overly complex HTML structures. Conversely, Vision-only generation often hallucinates specific hex colors or text content.

## Decision
We have adopted a **Hybrid Vision + Data Strategy**. 
The `LLMCoder` now sends two inputs to Gemini:
1.  **The Image (Visual Reference):** Used to determine layout, hierarchy, and alignment.
2.  **The JSON (Data Reference):** Used for exact text, colors, and spacing values.

A specific "Conflict Resolution" prompt instructs the AI to trust the Image for structure but the JSON for data.

## Consequences
### Positive
*   **Accuracy:** Generates "Pixel-Perfect" layouts while maintaining data fidelity.
*   **Robustness:** Handles messy Figma Frame hierarchies gracefully by "seeing" the intended result.

### Negative
*   **Latency:** Requires downloading and processing an image for every generation (mitigated by asynchronous fetching).
