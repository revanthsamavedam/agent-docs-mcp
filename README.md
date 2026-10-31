# agent-docs-mcp

Python MCP server for agent-docs, for GitHub Copilot integration.
Separate repo — it talks to the api repo over HTTP and never
imports its code or database.

## Scope — publish, view, version history, and shared state

Tools (eleven):

- `list_documents`
- `get_document`
- `create_document`
- `publish_document` (new immutable version)
- `list_versions`
- `get_version`
- `get_version_html`
- `get_document_state` — all shared state for a document
- `set_document_state` — set one key (null deletes it)
- `patch_document_state` — patch several keys at once
- `delete_document_state` — delete one key

Shared state is document-scoped, not version-scoped, and
changing it never creates a version. No comment, grant, or
approval tools. Documents are plain HTML; the MCP server never
writes React/JSX into a document.

## Configuration

- `AGENT_DOCS_API_URL` — api repo base URL.
  Default: `http://127.0.0.1:8000`
- `AGENT_DOCS_TOKEN` — optional token passed through as a Bearer
  token to the API. Placeholder seam only; it is never verified
  here and never printed. The deployer wires real identity.

## Run

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# stdio (local Copilot use)
.venv/bin/python -m agent_docs_mcp

# remote HTTP server (for a hosted MCP endpoint)
.venv/bin/python -m agent_docs_mcp --transport streamable-http --port 8001
```

## GitHub Copilot in VS Code — stdio (local)

In VS Code's `mcp.json`:

```json
{
  "servers": {
    "agent-docs": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "agent_docs_mcp"],
      "env": {
        "AGENT_DOCS_API_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

Run the api repo first (`python -m app.main` in that repo), then
ask Copilot to list, create, or publish an agent-docs document.

## GitHub Copilot — HTTP (remote)

Run the server with `--transport streamable-http`, then point
Copilot at the MCP endpoint, e.g. `http://127.0.0.1:8001/mcp`,
with an `Authorization` header carrying your placeholder token
(`Bearer EXAMPLE_TOKEN` is only a format example, not a real
credential). In production this endpoint sits behind real
identity/authorization, which the deployer wires.

## Tests

```
.venv/bin/python -m pytest -q
```

The tool-list test always runs. The live round-trip test runs
only when an api repo is reachable at `AGENT_DOCS_API_URL`
(and is skipped otherwise).
