# GitHub Configuration Guide 🐙

This guide will help you generate a **Personal Access Token (PAT)** and configure your `.env` file for the Figma-to-Code automation.

## 1. Generate a Personal Access Token

1.  Log in to [GitHub.com](https://github.com).
2.  Go to **Settings** (Click your profile picture -> Settings).
3.  Scroll down to **Developer settings** (bottom left).
4.  Click **Personal access tokens** -> **Tokens (classic)**.
5.  Click **Generate new token** -> **Generate new token (classic)**.
6.  **Note**: Give it a name like "Figma Bot".
7.  **Select Scopes** (Permissions):
    *   ✅ **repo** (Full control of private repositories) - *Required to create branches and PRs.*
    *   (Optional) **workflow** - *If you plan to trigger Actions.*
8.  Click **Generate token**.
9.  ⚠️ **Copy the token immediately**. You won't be able to see it again!

## 2. Locate Your Repository Name

The "Repository Name" is the part of the URL after `github.com/`.

*   Example URL: `https://github.com/torvalds/linux`
*   **Repository Name**: `torvalds/linux`
*   Format: `OwnerName/RepoName`

## 3. Update Your `.env` File

1.  Open the file named `.env` in this folder (rename `.env.example` if you haven't yet).
2.  Find the **GitHub Automation** section.
3.  Paste your values:

```env
# GitHub Automation
GITHUB_TOKEN=ghp_123456789abcde... (Paste your new token here)
GITHUB_REPO=your-username/your-repo-name
```

## 4. Verification

After saving the `.env` file, the MCP server will automatically verify access on startup.
