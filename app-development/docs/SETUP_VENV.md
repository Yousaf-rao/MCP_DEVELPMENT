# 🐍 Setting Up Your Virtual Environment

To avoid dependency conflicts with other tools (like ChromaDB or LiveKit), this project uses a Python Virtual Environment.

## 1. Create the Environment (Done)
The environment has been created in the `venv/` folder.

## 2. Activate the Environment ⚡
You must activate the environment **every time** you open a new terminal window to work on this project.

### Windows (PowerShell) - **Recommended**
```powershell
.\venv\Scripts\Activate.ps1
```
*(If you see an execution policy error, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first)*

### Windows (Command Prompt)
```cmd
venv\Scripts\activate.bat
```

### macOS / Linux
```bash
source venv/bin/activate
```

---

## 3. Install Dependencies 📦
Once activated (you should see `(venv)` in your prompt), install the project requirements:

```bash
pip install -r requirements.txt
```

## 4. Verify Setup ✅
Run this command to check if you are using the correct Python:

**Windows**: `where python` -> Should show `...\mcp_sprint1_bundle\venv\Scripts\python.exe`
**Mac/Linux**: `which python` -> Should show `.../mcp_sprint1_bundle/venv/bin/python`
