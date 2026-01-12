# Testing & verification Guide

This guide explains how to verify your MCP server functionalities using **MCP Inspector** and **Claude Desktop**.

## 1. Testing with MCP Inspector

The Inspector allows you to test tools interactively in your browser.

1.  Open your terminal in `app-development`:
    ```powershell
    cd c:\Users\Yousaf\Downloads\MCP-development\app-development
    ```
2.  Run the Inspector command:
    ```powershell
    npx @modelcontextprotocol/inspector ..\.venv\Scripts\python.exe mcp_server.py
    ```
3.  This will verify the server starts and open a URL (usually `http://localhost:5173`) in your browser.
4.  **Things to test in the Inspector UI**:
    - **Tools**: partial-types, list-tools.
    - Check if `figma`, `git`, and `filesystem` tools appear.
    - Try running `filesystem_read_file` on a known file (e.g., `README.md`) to verify access.

## 2. Using with Claude Desktop

To use these tools directly in Claude, you need to update your configuration file.

1.  Open the config file:
    - Press `Win+R`
    - Type `%APPDATA%\Claude` and hit Enter.
    - Open (or create) `claude_desktop_config.json`.

2.  Add this configuration:
    ```json
    {
      "mcpServers": {
        "repo-tools": {
          "command": "c:\\Users\\Yousaf\\Downloads\\MCP-development\\.venv\\Scripts\\python.exe",
          "args": [
            "c:\\Users\\Yousaf\\Downloads\\MCP-development\\app-development\\mcp_server.py"
          ]
        }
      }
    }
    ```
    *Note: If you already have other servers, add "repo-tools" to the existing "mcpServers" list.*

3.  **Restart Claude Desktop**.
4.  **Verify**: Look for the 🔌 icon in Claude. You should see "repo-tools" connected.
5.  **Try it out**: Ask Claude "Please list the files in my app-development project" or "Check my figma file".
