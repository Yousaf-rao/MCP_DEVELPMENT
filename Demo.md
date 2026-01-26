# LogicPatch: Technical Architecture & Design Document

**Version:** 1.0.0  
**Last Updated:** January 2026  
**Status:** Active / Production-Prototype

---

## 📖 1. Executive Summary

**LogicPatch** is a headless, autonomous software engineer that bridges the gap between Design (Figma) and Code (GitLab) without human intervention.

Unlike traditional "Figma-to-React" plugins that generate isolated code snippets, LogicPatch functions as an **Agent**. It lives in your repository, understands your existing project structure, monitors design changes in real-time, and submits Pull Requests like a human colleague.

### Core Philosophy
1.  **Autonomous:** No buttons to click. Changes in Figma trigger code updates automatically.
2.  **Context-Aware:** It doesn't just guess; it reads your existing codebase (via RAG) to match your coding style.
3.  **Safe:** It never pushes directly to `main`. All changes are submitted as Merge Requests (MRs) for human review.
4.  **Self-Healing:** If the generated code fails compilation, the agent catches the error and fixes itself before you ever see it.

---

## 🏗️ 2. High-Level Architecture

The system follows an **Event-Driven Architecture** composed of three decoupled micro-services.

```mermaid
graph TD
    subgraph "External World"
        Figma[Figma Platform]
        GitLab[GitLab Repositories]
    end

    subgraph "LogicPatch Core"
        Listener[Webhook Server (FastAPI)]
        DB[(Event Ledger / SQLite)]
        Worker[Automation Worker (Daemon)]
        Brain[Gemini 1.5 Flash (Vision AI)]
        Memory[ChromaDB (Vector Store)]
    end

    Figma --"Webhook (JSON)"--> Listener
    Listener --"Queue Event"--> DB
    DB --"Poll Pending"--> Worker
    Worker --"Read Context"--> Memory
    Worker --"Visual Analysis"--> Brain
    Brain --"React Code"--> Worker
    Worker --"Validation Loop"--> Worker
    Worker --"Merge Request"--> GitLab

```

---

## 🧠 3. Component Deep Dive

### 3.1. The Webhook Listener (`webhook_server.py`)

**Role:** The "Ears" of the system.

**Tech:** FastAPI, Uvicorn, SQLite.

* **Why FastAPI?** We need high-performance, asynchronous handling to respond to Figma's pings instantly (preventing timeouts).
* **The "CommentOps" Logic:**
* Instead of syncing every pixel movement (which is noisy/expensive), the server listens for **Comments**.
* **Trigger:** When a designer types `!sync` on a frame.
* **Mechanism:** The server parses the comment, extracts the `node_id`, and queues a "Targeted Job." This saves 90% of API costs and gives designers control.



### 3.2. The Automation Worker (`automation_worker.py`)

**Role:** The "Brain" and "Hands." It processes the queue.

**Tech:** Python AsyncIO, Custom Logic.

The worker is a continuous loop that performs the heavy lifting. It features two critical proprietary logic systems:

#### A. The "Hunter" Strategy (File Resolution)

How does the agent know *where* to put the code? It uses a 3-layer fallback system:

1. **Layer 1: Deterministic Match (Sanitized Name)**
* *Input:* Figma Frame "User Profile"
* *Action:* Sanitizes to "UserProfile" -> Searches file system.
* *Result:* Finds `FigmaDesign/UserProfile.jsx`. Updates it.
* *Why:* Fast, accurate, and handles spaces/casing differences.


2. **Layer 2: Visual Fingerprint (RAG Search)**
* *Input:* Frame Name "Frame 123" (Bad name)
* *Action:* Agent reads text inside the frame: "Login", "Password", "Forgot?".
* *Search:* Vectors search the codebase for files containing those terms.
* *Result:* Finds `LoginForm.jsx`. Updates it.
* *Why:* Survives bad naming conventions by "reading" the design.


3. **Layer 3: Creation Fallback**
* *Action:* If no match is found, creates a NEW file in `FigmaDesign/`.
* *Why:* Prevents overwriting unrelated files and keeps new AI code isolated.



#### B. The Self-Healing Validation Loop

Before pushing code, the worker runs a "Compiler Check" (simulated or actual linting).

* **Step 1:** Generate Code.
* **Step 2:** Validate.
* **Step 3:** **If Error:** Feed the error message *back* to Gemini ("You missed a closing bracket on line 42").
* **Step 4:** Regenerate & Retry.
* **Result:** You rarely see broken code in your PRs.

### 3.3. The Intelligence Engine (`LLMCoder` + Gemini 1.5)

**Role:** The "Coder."

**Tech:** Google Gemini 1.5 Flash.

* **Why Gemini 1.5 Flash?**
* **Vision Native:** It creates code directly from the image pixels, capturing spacing, colors, and layout that JSON extraction often misses.
* **Long Context Window:** We feed it your `tailwind.config.js` and `global.css` so it knows *your* design variables.


* **Context injection:** We don't just say "Make a button." We say "Make a button using *these* Tailwind colors defined in the user's config."

### 3.4. Vector Memory (`RepoSearch` + ChromaDB)

**Role:** The "Long-term Memory."

**Tech:** ChromaDB (Local vector store).

* **Why use RAG (Retrieval-Augmented Generation)?**
* Standard LLMs "hallucinate" generic styles (e.g., standard Bootstrap blue).
* **Our Solution:** We index your entire repository. When generating a "Login" component, we retrieve *other* forms from your repo and show them to the AI.
* **Result:** The AI mimics your existing coding style, naming conventions, and import patterns.



---

## 🔄 4. The Workflow Data Flow

### Scenario: Updating the "UserProfile" Component

1. **Designer:** Changes the avatar size in Figma. Comments `!sync`.
2. **Listener:** Receives webhook. Verifies secret. Adds job `job_123` to SQLite. Returns `200 OK`.
3. **Worker (Tick 1):** Wakes up. Sees `job_123`.
4. **Worker (Fetch):** Hits Figma API. Downloads the node JSON and a PNG snapshot.
5. **Worker (Hunter):**
* Checks for `UserProfile.jsx`? **Found.**
* Reads `tailwind.config.js`.


6. **AI Generation:**
* Input: Image + JSON + Tailwind Config + Existing File Content.
* Prompt: "Update this React component to match the new image. Keep existing logic."


7. **Validator:** Checks syntax. **Pass.**
8. **GitLab:**
* Checks out branch `figma-pipeline`.
* Commits changes.
* Pushes to remote.
* Creates/Updates Merge Request.


9. **Designer:** Sees a notification on GitLab: "MR Created: Update UserProfile from Figma."

---

## 🔒 5. Security & Hardening

* **Jailbreak Protection:**
* The file system tools are restricted to the `SEARCH_ROOT` (currently `.` for repository-wide search). The agent creates new files in `FigmaDesign/` folder.


* **Secret Management:**
* All API keys (Figma, GitLab, Gemini) are loaded via `.env` and never logged to the console.


* **Human-in-the-Loop:**
* The agent **never** pushes to `main`. It effectively requires a human "Sign-off" (Merge) for every action.



---

## 🛠️ 6. Configuration Reference

Key variables controlling the architecture in `.env`:

| Variable | Purpose | Recommended Value |
| --- | --- | --- |
| `SEARCH_ROOT` | **Critical.** Defines the "Sandbox" where the agent looks for existing code. New files go to `FigmaDesign/`. | `.` (repository root) |
| `DEBOUNCE_WINDOW` | Prevents spamming AI calls if a designer moves a box 5 times in 1 second. | `30` (seconds) |
| `GITLAB_BRANCH` | The working branch for the robot. | `figma-pipeline` |
| `MCP_AUTO_APPROVE` | Development mode flag. | `true` (for dev), `false` (for prod) |

---

## 🔮 7. Future Roadmap

1. **Multi-File Generation:** Allowing the agent to create a Component file + a CSS file + a Test file simultaneously.
2. **Storybook Integration:** Automatically creating Storybook stories for new components.
3. **Two-Way Sync:** (Experimental) Updating Figma text when code changes (e.g., translation keys).
4. **Auto-Startup:** New `start_logicpatch.bat` script handles ngrok, webhook registration, and service startup automatically.