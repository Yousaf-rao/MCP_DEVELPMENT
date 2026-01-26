# 🎭 The "Headless Engineer" Demo Script

**Objective:** Demonstrate that this is not just a code generator, but an **Autonomous Agent** that integrates into existing workflows, understands context, and safeguards its own work.

**Target Audience:** Engineers, Product Managers, or Stakeholders.

---

## 🎬 Pre-Show Setup (Do this 5 mins before)

1.  **Clear the Stage:**
    ```bash
    rm events.db
    python scripts/init_db.py
    ```
2.  **Open 3 Terminal Tabs/Windows:**
    *   **Tab 1 (Server):** `python webhook_server.py`
    *   **Tab 2 (Trigger):** `cd scripts` (Ready to run `simulate_webhook.py`)
    *   **Tab 3 (The Star):** `python automation_worker.py` (Leave this running to show the "Indexing" log)
3.  **Open VS Code Files:**
    *   `.env` (Show the Repo Config)
    *   `mcp_core/utils/validator.py` (Show the Self-Healing logic)

---

## 🎬 Act 1: The Drop-In Contractor (CI/CD)

**Goal:** Show that the agent is decoupled from the codebase.

**👀 Visuals:**
*   Show `.env` file.
*   Highlight `GITLAB_REPO_URL`.

**🎤 Voiceover:**
> "Most AI coding tools are stuck inside your IDE. They only know about the file you have open."
> 
> "This agent is different. It's a **Headless Engineer**. I can drop it into any environment, give it a Git URL, and it gets to work."
> 
> "Here in my config, I'm pointing it to a completely remote repository: `aurum-byte/SORB-PLRA`. I haven't even cloned this repo myself. The Agent handles everything."

---

## 🎬 Act 2: Assessment & Indexing

**Goal:** Show the "RAG" (Retrieval Augmented Generation) capability.

**👀 Visuals:**
*   Switch to **Tab 3** (Automation Worker).
*   Restart the worker (`Ctrl+C`, `Up Arrow`, `Enter`).

**🎤 Voiceover:**
> "Watch what happens when I start the worker."
> 
> *(Wait for 'Connecting to Remote...' log)*
> "First, it connects to GitLab and clones the latest version of the code into a secure sandbox."
> 
> *(Wait for 'Indexing...' log)*
> "Now, look at that: **'Indexing files into Vector DB'**. It's building a mental map of the entire project. It's learning your folder structure, your naming conventions, and your utility functions. It's essentially 'Reading the Docs' before it writes a single line of code."

---

## 🎬 Act 3: The Trigger (Debounce & Vision)

**Goal:** Show that the agent treats inputs intelligently, not just reactively.

**👀 Visuals:**
*   Switch to **Tab 2** (Trigger).
*   Run: `python simulate_webhook.py`
*   Switch quickly back to **Tab 3** (Worker).

**🎤 Voiceover:**
> "I'm going to simulate a designer making a change in Figma."
> 
> *(Run Simulation)*
> 
> "Now, watch the worker logs. It sees the event... but it doesn't rush."
> 
> *(Point to 'Debounce settled' log)*
> "It waits 30 seconds. Why? Because designers save constantly. If we ran on every save, we'd break the build. This agent has patience. It waits for the 'Quiet Period' to ensure the design is stable."

**👀 Vision Highlight:**
> *(Point to 'Downloaded vision test image' log)*
> "And look here. It downloaded the image. It's not just reading the layer names; it's **looking** at the pixel layout to understand spacing and alignment."

---

## 🎬 Act 4: Context-Aware Coding

**Goal:** Show that it writes code that *fits* the project.

**👀 Visuals:**
*   Scroll to the `Vector Search querying...` log.

**🎤 Voiceover:**
> "Before it writes code, it asks questions."
> 
> "It uses Vector Search to find relevant files. It found `Calorie_Webapp`... it sees how similar components are built. It's not hallucinating a style; it's mimicking the existing project structure."

---

## 🎬 Act 5: The Safety Net (Self-Healing)

**Goal:** The "Wow" moment. The agent fixes its own mistakes.

**👀 Visuals:**
*   Look for `🛡️ Running Compiler Check...` in logs.

**🎤 Voiceover:**
> "This is the most critical part. Most AI writes buggy code and leaves you to fix it."
> 
> "This agent runs a **code validation check** inside the project environment. It actually tries to verify the code."
> 
> "If it sees an error—maybe a missing import or a syntax issue—it reads the error message, rewrites the code, and tries again. It has a **Self-Healing Loop**."
> 
> "It will NEVER push broken code to your branch. If it can't fix it, it aborts."

---

## 🎬 Finale: The Delivery

**Goal:** Show the tangible output.

**👀 Visuals:**
*   Show the final log: `✅ Success! MR: https://gitlab.com/...`

**🎤 Voiceover:**
> "And there it is. A verified, compiled, formatted Merge Request, waiting on GitLab."
> 
> "We went from a design change to a safe code update without a human lifting a finger."

---

## 🧪 Quick Reference Checklist

*   [ ] **Server Running?** (Port 8000)
*   [ ] **Worker Running?** (Check env vars)
*   [ ] **Sufficient Quota?** (Check Gemini limits)
*   [ ] **Clean State?** (Did you delete old `temp_workspace` if needed?)
