# 🐍 Setup Guide: Virtual Environment

Follow these steps to set up the Python environment for the **Gemini-Powered Headless Engineer**.

## 1. Prerequisites
*   **Python 3.10** or higher (Required for some RAG libraries).
*   **Git** installed and available in terminal.

## 2. Create Virtual Environment

### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Mac / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Dependencies
This will install `google-generativeai`, `chromadb`, `sentence-transformers`, `fastapi`, and more.

```bash
pip install -r requirements.txt
```

> **Note:** If `chromadb` fails to install on Windows, ensure you have the "C++ Build Tools" installed via Visual Studio Installer, or try: `pip install chromadb-client`.

## 4. Verify Installation
Run this quick check to ensure your environment is ready:

```bash
python -c "import google.generativeai; import chromadb; print('✅ Environment Ready!')"
```

## 5. Next Steps
Move on to **Configuration**:
1.  Copy `.env.example` to `.env`.
2.  Add your keys (`GEMINI_API_KEY`, `FIGMA_TOKEN`, etc.).
3.  Run the server!
