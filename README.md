# agent-docs-mcp

Python MCP server for agent-docs, for GitHub Copilot integration.
Separate repo — it talks to the api repo over HTTP and never
imports its code or database.

## Scope — publish, view, version history, and shared state

Tools (sixteen):

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
changing it never creates a version.

API registry (onboard an internal API once, use it in any
document at view time; stores URLs only, never tokens):

- `register_api` — register `{name, api_url, token_url, scope?, app?, swagger_url?}`
- `list_apis`, `get_api`, `delete_api`
- `sync_apis_from_swagger` — fetch the latest Swagger doc for an
  app and update its registry entry; with `swagger_url` that URL
  is stored in the app config, without it the stored URL is used

No comment, grant, or approval tools. Documents are plain
HTML; the MCP server never writes React/JSX into a document.

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

## Copilot instructions

Copy `docs/copilot-instructions.md` from this repo to
`.github/copilot-instructions.md` in the project where Copilot
builds agent-docs pages. VS Code Copilot reads that file
automatically, so Copilot follows the agent-docs rules without
being told them every time: documents are plain self-contained
HTML, live data only via `window.agentdocs.apiFetch`, never a
token in published HTML, publish with `base_version_id` and
handle a 409 by re-fetching, and navigation via the viewer nav
bar or `window.agentdocs.navigate`.

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
