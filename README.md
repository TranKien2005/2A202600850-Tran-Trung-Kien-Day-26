# Lab: Build a Database MCP Server with FastMCP and SQLite

## Goal

Build a Model Context Protocol (MCP) server using FastMCP that exposes a small database through:

- `search`
- `insert`
- `aggregate`

You must also expose the database schema as an MCP resource, test the server with Inspector or equivalent tooling, and show the server working from at least one MCP client.

## Learning Outcomes

By the end of this lab, students should be able to:

- explain what MCP tools and resources are
- build a FastMCP server in Python
- connect FastMCP to a SQLite database
- safely validate database requests before executing SQL
- expose dynamic schema context through `@mcp.resource(...)`
- test tool schemas, normal calls, and error responses
- connect the server to an MCP client such as Claude Code, Codex, or Gemini CLI

## Required Features

### Part 1: MCP Server

Implement a FastMCP server that exposes exactly these tool categories:

1. `search`
2. `insert`
3. `aggregate`

Your server may use SQLite for the main implementation. If you want to support PostgreSQL too, design the code so the database layer can be swapped later.

### Part 2: Resource

Expose database schema information as MCP resources:

- one resource for the full database schema
- one dynamic resource template for a single table schema

Suggested URIs:

- `schema://database`
- `schema://table/{table_name}`

### Part 3: Validation and Error Handling

Your tools must reject unsafe or invalid requests:

- unknown table names
- unknown column names
- unsupported filter operators
- invalid aggregate requests
- empty inserts

Do not build SQL by blindly concatenating raw user input.

### Part 4: Testing and Verification

Verify all of the following:

1. the server starts correctly
2. the three tools are discoverable
3. the schema resource is discoverable
4. valid tool calls return useful results
5. invalid tool calls return clear errors
6. at least one MCP client can connect and use the server

### Part 5: Demo Deliverables

Prepare:

- GitHub repository
- setup instructions
- tool descriptions
- testing steps
- at least one client configuration example
- short demo video, around 2 minutes

Inspector screenshots are recommended if you use MCP Inspector.

## Suggested Project Structure

```text
implementation/
  db.py
  init_db.py
  mcp_server.py
  verify_server.py
  tests/
    test_server.py
```

## Recommended Data Model

Use a small relational dataset so `search`, `insert`, and `aggregate` are easy to demo. Example:

- `students`
- `courses`
- `enrollments`

## Example Tasks to Demonstrate

- search all students in cohort `A1`
- insert a new student
- count rows in a table
- compute average score by cohort
- read the full schema resource
- read `schema://table/students`
- show an invalid request, such as searching a missing table

## FastMCP and Inspector References

- FastMCP quickstart: https://gofastmcp.com/v2/getting-started/quickstart
- FastMCP resources: https://gofastmcp.com/v2/servers/resources
- MCP Inspector: https://modelcontextprotocol.io/docs/tools/inspector

## Client Setup Notes

### Claude Code

Anthropic documents local JSON config and `claude mcp add` flows here:

- https://code.claude.com/docs/en/mcp

Claude Code supports MCP resources via `@server:resource-uri` references and supports environment variable expansion in `.mcp.json`.

### Codex

OpenAI documents Codex MCP setup here:

- https://developers.openai.com/learn/docs-mcp

Codex supports MCP server configuration through the CLI and `~/.codex/config.toml`.

### Gemini CLI

Gemini CLI has a built-in MCP manager. In the verified local workflow, the simplest path is:

```bash
gemini mcp add sqlite-lab /ABSOLUTE/PATH/TO/python /ABSOLUTE/PATH/TO/implementation/mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
```

Gemini CLI also documents configuration details here:

- https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md

Expected outcome:

- the server appears as `Connected`
- Gemini can discover `search`, `insert`, and `aggregate`
- a headless smoke test works with `gemini --allowed-mcp-server-names sqlite-lab --yolo -p "..."`

### Antigravity

Antigravity commonly uses an `mcp_config.json` file with a shape similar to Gemini CLI. Verify the current product behavior in your installed version before grading against exact UI steps.

## Deliverable Checklist

- working FastMCP server
- SQLite database and seed data
- `search`, `insert`, `aggregate` tools
- schema resource and schema resource template
- verification steps
- automated tests or repeatable verification script
- client configuration example
- README with setup and demo steps
- Inspector startup command or helper script
- at least one verified Gemini CLI or Claude/Codex client test

## Bonus

Optional bonus:

- add authentication for SSE or HTTP transport
- support both SQLite and PostgreSQL with the same MCP surface
- add richer output annotations or pagination

---

## How to Setup and Run the Server

### 1. Installation
Install the required packages in your Python environment:
```bash
pip install fastmcp python-dotenv
```

### 2. Environment Configuration
Create a `.env` file in the root directory and add the Ollama Cloud credentials:
```env
OPENAI_API_KEY=9f057841300d4ac9abc0808db64d476c.72plWH8uOSz1Cfb3XdtYoQvN
OPENAI_BASE_URL=https://ollama.com/v1
LLM_MODEL=gpt-oss:120b
```

### 3. Initialize and Seed the Database
Run the script to create and seed the SQLite database:
```bash
python implementation/init_db.py
```
This generates the database at `implementation/school.db`.

### 4. Running Verification Checks
Execute the programmatic verification script to run search, insert, and aggregation tools as well as retrieve database schemas:
```bash
python -X utf8 implementation/verify_server.py
```

### 5. Running Automated Tests
Run the automated test suite using `pytest`:
```bash
pytest -v implementation/tests/test_server.py
```

### 6. Starting MCP Inspector
You can inspect the server using the MCP Inspector tool:
```bash
npx @modelcontextprotocol/inspector python implementation/mcp_server.py
```

### 7. Screenshots for Reporting
The screenshots verifying the server's functionality have been saved in the [screenshots/](file:///D:/My%20Works/Coding/Practice/2A202600850-Tran-Trung-Kien-Day-26/screenshots) folder:
*   `media__1782964989257.png`: Discoverable tools list in the inspector (`search`, `insert`, `aggregate`).
*   `media__1782965012821.png` & `media__1782965033263.png`: Reading database schema and tool execution views.
*   `media__1782964644638.png` & `media__1782965033263.png`: Verification of validation and security error handling.

### 8. Demo Video
The project demonstration video is available at:
*   [Google Drive Demo Video](https://drive.google.com/file/d/1wLGyeNZMtblA-qBafoDFlbjBddIt0N73/view?usp=drive_link)

### 9. Connecting to Gemini CLI
You can connect this server directly to the Gemini CLI by running:
```bash
gemini mcp add sqlite-lab python /ABSOLUTE/PATH/TO/implementation/mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
```
Then run tasks like:
```bash
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Show the average score by cohort using the sqlite-lab server."
```