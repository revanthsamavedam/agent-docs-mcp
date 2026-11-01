"""MCP tests: exactly the locked tool list, plus an optional live-API round trip.

The live test is skipped when no API is reachable, so the suite
passes standalone; run it against a live API to exercise the
end-to-end path.
"""

import asyncio
import os

import httpx
import pytest

from agent_docs_mcp.server import (
    create_document,
    get_document,
    get_version_html,
    list_documents,
    list_versions,
    mcp,
    publish_document,
)

EXPECTED_TOOLS = {
    "list_documents",
    "get_document",
    "create_document",
    "publish_document",
    "list_versions",
    "get_version",
    "get_version_html",
    "get_document_state",
    "set_document_state",
    "patch_document_state",
    "delete_document_state",
    "register_api",
    "list_apis",
    "get_api",
    "delete_api",
    "sync_apis_from_swagger",
}


def test_tool_list_is_exactly_the_locked_set():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS, names
    # No comment/grant/approval tools may creep in.
    assert not (names & {"create_comment", "list_comments", "grant", "approve"})


def _api_reachable() -> bool:
    base = os.environ.get("AGENT_DOCS_API_URL", "http://127.0.0.1:8000")
    try:
        httpx.get(f"{base}/health", timeout=2, trust_env=False).raise_for_status()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _api_reachable(), reason="agent-docs API not running")
def test_live_create_publish_get_round_trip():
    html_v1 = "<!doctype html><html><body><h1>MCP v1</h1></body></html>"
    html_v2 = "<!doctype html><html><body><h1>MCP v2</h1></body></html>"
    created = create_document("MCP round trip", html_v1, "v1")
    doc_id = created["id"]
    v1_id = created["version"]["id"]

    published = publish_document(doc_id, html_v2, v1_id, "v2")
    assert published["version"]["number"] == 2

    assert get_document(doc_id)["latest_version"]["number"] == 2
    versions = list_versions(doc_id)["versions"]
    assert [v["number"] for v in versions] == [1, 2]
    assert get_version_html(doc_id, v1_id) == html_v1
    docs = list_documents()["documents"]
    assert any(d["id"] == doc_id for d in docs)
