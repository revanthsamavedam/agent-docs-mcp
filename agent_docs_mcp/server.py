"""agent-docs MCP server for GitHub Copilot integration.

Tools (publish, view, version history, shared state, API registry, drafts):
  list_documents, get_document, create_document, publish_document,
  list_versions, get_version, get_version_html,
  get_document_state, set_document_state, patch_document_state,
  delete_document_state,
  register_api, list_apis, get_api, delete_api,
  get_copilot_instructions

get_copilot_instructions returns the bundled Copilot instructions
text on demand. It writes nothing and fetches nothing remote: the
text ships with this package (agent_docs_mcp/copilot_instructions.md,
mirrored from docs/copilot-instructions.md), so Copilot gets the
current rules without a CLI fetch or a .github file. Copying that
text to .github/copilot-instructions.md in a project is still the
way to make VS Code apply it automatically.

State tools call the API's document-scoped KV store: state
survives across versions and changing it never creates a
version. No comment, grant, or approval tools.

The tools call the agent-docs API over HTTP. They never import
code from the api repo and never touch its database. API base URL
comes from AGENT_DOCS_API_URL (default http://127.0.0.1:8000).
An optional AGENT_DOCS_TOKEN is sent as a Bearer token and is
never printed or logged.

Auth is a placeholder seam only: the token is passed through to
the API, which itself does not verify it against a real identity
provider. The deployer wires real identity/authorization.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("agent-docs")


def _instructions_text() -> tuple[str, str]:
    """Bundled instructions text, and where it came from.

    Bundled copy first (works from a pip install), repo docs copy
    second (works from a source checkout). No remote fetch, ever.
    """
    bundled = Path(__file__).parent / "copilot_instructions.md"
    if bundled.is_file():
        return bundled.read_text(encoding="utf-8"), "bundled"
    docs = Path(__file__).parent.parent / "docs" / "copilot-instructions.md"
    if docs.is_file():
        return docs.read_text(encoding="utf-8"), "docs"
    raise FileNotFoundError("copilot instructions not found in package or docs")


def api_base_url() -> str:
    return os.environ.get("AGENT_DOCS_API_URL", "http://127.0.0.1:8000").rstrip("/")


# trust_env=False on every httpx client: the API URL is a configured
# internal/local URL and must never be routed through an ambient
# HTTP proxy, and bracketed IPv6 entries in no_proxy break httpx's
# proxy URL parsing. The API client therefore ignores proxy env vars.
def _headers() -> dict[str, str]:
    token = os.environ.get("AGENT_DOCS_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _get(path: str):
    with httpx.Client(base_url=api_base_url(), headers=_headers(), timeout=30, trust_env=False) as c:
        r = c.get(path)
        r.raise_for_status()
        return r.json()


def _post(path: str, payload: dict):
    with httpx.Client(base_url=api_base_url(), headers=_headers(), timeout=30, trust_env=False) as c:
        r = c.post(path, json=payload)
        r.raise_for_status()
        return r.json()


def _put(path: str, payload: dict):
    with httpx.Client(base_url=api_base_url(), headers=_headers(), timeout=30, trust_env=False) as c:
        r = c.put(path, json=payload)
        r.raise_for_status()
        return r.json()


def _delete(path: str):
    with httpx.Client(base_url=api_base_url(), headers=_headers(), timeout=30, trust_env=False) as c:
        r = c.delete(path)
        r.raise_for_status()
        return r.json()


def _get_text(path: str) -> str:
    with httpx.Client(base_url=api_base_url(), headers=_headers(), timeout=30, trust_env=False) as c:
        r = c.get(path)
        r.raise_for_status()
        return r.text


@mcp.tool()
def list_documents() -> dict:
    """List agent-docs documents (id, title, latest version)."""
    return _get("/v1/documents")


@mcp.tool()
def get_document(document_id: str) -> dict:
    """Get one document with its latest version."""
    return _get(f"/v1/documents/{document_id}")


@mcp.tool()
def create_document(title: str, html: str, change_summary: str = "") -> dict:
    """Create a document from plain HTML; stores version 1."""
    return _post(
        "/v1/documents",
        {"title": title, "html": html, "change_summary": change_summary},
    )


@mcp.tool()
def publish_document(
    document_id: str, html: str, base_version_id: str, change_summary: str = ""
) -> dict:
    """Publish a new immutable version. base_version_id must be current;
    a stale base returns a 409 from the API."""
    return _post(
        f"/v1/documents/{document_id}/versions",
        {
            "html": html,
            "base_version_id": base_version_id,
            "change_summary": change_summary,
        },
    )


@mcp.tool()
def create_draft_document(title: str, html: str) -> dict:
    """Create a draft-only document: no version yet. View it on the
    actual viewer link (?doc=<id>&draft=1), then publish_draft when
    it looks right. A draft is validated like a publish, but a
    rejected draft stores nothing."""
    return _post("/v1/documents", {"title": title, "html": html, "draft": True})


@mcp.tool()
def save_draft(document_id: str, html: str) -> dict:
    """Save an unpublished draft for an existing document. Creates
    no version and touches no published version; view it at
    ?doc=<id>&draft=1 on the actual viewer link."""
    return _put(f"/v1/documents/{document_id}/draft", {"html": html})


@mcp.tool()
def publish_draft(document_id: str, change_summary: str = "") -> dict:
    """Publish the stored draft as the next version; clears it.
    Fails when there is no draft."""
    return _post(f"/v1/documents/{document_id}/draft/publish", {"change_summary": change_summary})


@mcp.tool()
def list_versions(document_id: str) -> dict:
    """List a document's versions (metadata only, oldest first)."""
    return _get(f"/v1/documents/{document_id}/versions")


@mcp.tool()
def get_version(document_id: str, version_id: str) -> dict:
    """Get one version's metadata (number, sha256, change summary)."""
    return _get(f"/v1/documents/{document_id}/versions/{version_id}")


@mcp.tool()
def get_version_html(document_id: str, version_id: str) -> str:
    """Get one version's raw HTML, byte-identical to what was published."""
    return _get_text(f"/v1/documents/{document_id}/versions/{version_id}/html")


@mcp.tool()
def get_document_state(document_id: str) -> dict:
    """Get a document's shared state (all keys). State is document-scoped, not version-scoped."""
    return _get(f"/v1/documents/{document_id}/state")


@mcp.tool()
def set_document_state(document_id: str, key: str, value) -> dict:
    """Set one shared-state key. A null value deletes the key."""
    return _put(f"/v1/documents/{document_id}/state/{key}", {"value": value})


@mcp.tool()
def patch_document_state(document_id: str, patch: dict) -> dict:
    """Patch several shared-state keys at once; null values delete those keys."""
    return _post(f"/v1/documents/{document_id}/state", {"patch": patch})


@mcp.tool()
def delete_document_state(document_id: str, key: str) -> dict:
    """Delete one shared-state key."""
    return _delete(f"/v1/documents/{document_id}/state/{key}")


@mcp.tool()
def register_api(name: str, api_url: str, token_url: str, scope: str = "", app: str = "", swagger_url: str = "") -> dict:
    """Register an internal API for documents to use at view time: app short name, base URL, per-endpoint token URL, and optional Swagger doc URL stored in its app config. Stores URLs only, never tokens."""
    payload = {"name": name, "api_url": api_url, "token_url": token_url, "scope": scope}
    if app:
        payload["app"] = app
    if swagger_url:
        payload["swagger_url"] = swagger_url
    return _post("/v1/apis", payload)


@mcp.tool()
def list_apis(app: str = "") -> dict:
    """List registered internal APIs, optionally for one app."""
    return _get(f"/v1/apis?app={app}" if app else "/v1/apis")


@mcp.tool()
def sync_apis_from_swagger(app: str, swagger_url: str = "") -> dict:
    """Fetch the latest Swagger doc for an app and update its registry entry.

    With swagger_url, that URL is stored in the app config; without
    it, the stored swagger_url is used, so a later sync needs no URL.
    Base URL comes from servers[0].url, endpoints from paths, token
    URL from the Swagger oauth2 tokenUrl if present else the existing
    token URL is kept. Removed endpoints are reported, never auto-deleted.
    """
    return _post(f"/v1/apis/{app}/sync", {"swagger_url": swagger_url} if swagger_url else {})


@mcp.tool()
def get_copilot_instructions() -> dict:
    """Return the agent-docs rules Copilot should follow when building pages.

    On-demand, local, bundled text — no file is written and nothing
    is fetched remotely. Follow these rules for every agent-docs page:
    plain self-contained HTML, live data only via window.agentdocs.apiFetch,
    never a token in published HTML, publish with base_version_id and
    handle a 409 by re-fetching. For automatic application in VS Code,
    copy this text to .github/copilot-instructions.md in the project.
    """
    text, source = _instructions_text()
    return {
        "instructions": text,
        "source": source,
        "apply_automatically": ".github/copilot-instructions.md",
    }


@mcp.tool()
def get_api(name: str) -> dict:
    """Get one registered internal API."""
    return _get(f"/v1/apis/{name}")


@mcp.tool()
def delete_api(name: str) -> dict:
    """Remove a registered internal API."""
    return _delete(f"/v1/apis/{name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="agent-docs MCP server")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http"],
        help="stdio for local Copilot use; streamable-http for a remote server",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
