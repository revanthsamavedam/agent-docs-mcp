"""agent-docs MCP server for GitHub Copilot integration.

Tools only (publish, view, version history):
  list_documents, get_document, create_document, publish_document,
  list_versions, get_version, get_version_html

Note on count: the locked tool list names seven tools, not six.
This server exposes exactly those seven, and nothing else — no
comment, state, grant, or approval tools.

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

import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("agent-docs")


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
