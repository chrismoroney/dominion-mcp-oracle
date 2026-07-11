# Dominion Oracle: Setup & Contributor Guide

Welcome to the team! This guide will get your local development environment running so you can start contributing to the **Dominion Analytics & MCP Oracle**.

## 1. Prerequisites

Before starting, ensure you have the following installed:
* **Python 3.10+**: [Download here](https://www.python.org/downloads/)
* **Git**: [Download here](https://git-scm.com/)
* **Claude Desktop App**: [Download here](https://claude.ai/download) (Required for the MCP interface)
* **Neon PostgreSQL Account**: You will need your own connection string to your database.

---

## 2. File Structure

Your project directory should look like this. Make sure everything is in its proper place:

```text
DOMINION-MCP-ORACLE/
├── mcp/
│   └── mcp_oracle.py       # The core FastMCP server and tools script
├── .env                    # Local environment variables (DO NOT COMMIT)
├── .gitignore              # Tells Git which files to ignore
├── requirements.txt        # Python dependencies list
├── SETUP.md                # This setup guide
└── README.md               # Main repository documentation

## 3. Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd dominion-mcp-oracle
   ```

2. **Setup Virtual Environment:**
   It is critical to isolate dependencies. Create a virtual environment and activate it:
   ```bash
   # Create the venv
   python -m venv venv

   # Activate it
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   .\venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 4. Configuration

### Step A: Protect Your Files (`.gitignore`)
Create a file named `.gitignore` in your root directory and paste the following block into it to ensure you don't accidentally leak secrets or bloat the repository:

```text
# Security & Environment Variables
.env
.env.*
*.env

# Virtual Environments & Dependencies
venv/
.venv/
env/
ENV/
pyvenv.cfg
requirements.txt.bak

# Python Cache & Compiled Files
__pycache__/
*.py[cod]
*$py.class

# OS Specific Junk
.DS_Store
.DS_Store?
._*
Thumbs.db
```

### Step B: Database Connection (`.env`)
Create a `.env` file in the root directory. **Do not commit this file to Git.**
```text
DATABASE_URL=postgresql://your_neon_connection_string_here
```

### Step C: Claude Desktop Integration (`claude_desktop_config.json`)
Claude needs to know exactly where your Python environment lives on your hard drive. 

1. **Open (or create) the Claude config file:**
   * **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   * **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add the following entry.** 
   * *Important*: You must find your absolute project path (run `pwd` in your project terminal) and replace `/YOUR_ABSOLUTE_PATH_TO/` with your actual machine path. Do not use relative paths.

```json
{
  "mcpServers": {
    "dominion_oracle": {
      "command": "/YOUR_ABSOLUTE_PATH_TO/dominion-mcp-oracle/venv/bin/python",
      "args": [
        "/YOUR_ABSOLUTE_PATH_TO/dominion-mcp-oracle/mcp/mcp_oracle.py"
      ],
      "env": {
        "DATABASE_URL": "postgresql://your_neon_connection_string_here"
      }
    }
  }
}
```

3. **Restart the Claude Desktop App** completely to load the configuration (Right-click icon -> Quit, then relaunch). Look for a "Hammer" or "Plug" icon in the chat interface to verify the connection.

---

## 5. Testing the Integration

### Manual Developer Testing (No AI required)
If you want to manually test your database pipes without using Claude, run the FastMCP inspector from your virtual environment terminal:
```bash
mcp dev mcp/mcp_oracle.py
```
This opens a web UI at `http://localhost:5173` where you can manually click `List Tools` and test individual inputs.

### Natural Language AI Testing
Open the Claude Desktop app. If the server is loaded, type or speak this prompt to verify the agentic workflow is operational:

> "Hey Claude, please start a new game called G-500 using the Base 2E expansion. I'm player P001. On turn 1, I played a Smithy, drew 3 Coppers, and bought a Silver."

Watch the UI to confirm Claude autonomously executes your database commands across multiple sequential tool steps.

---

## 6. Troubleshooting
* **Server Disconnected?** If you see a connection error in Claude, it is almost certainly a path mismatch in the JSON config. Ensure the `command` path points exactly to the executable file inside your `venv/bin/python` or `venv\Scripts\python.exe`.
* **Stray Python Interpreters:** Ensure you aren't referencing the global system Python in your Claude config file, or you may hit a `SyntaxError: Non-UTF-8 code` error as the machine attempts to parse a binary execution block as plain text.
* **Checking Logs:** If you get stuck, view the background crash output using:
  * **macOS**: `tail -n 50 ~/Library/Logs/Claude/mcp-server-dominion_oracle.log`