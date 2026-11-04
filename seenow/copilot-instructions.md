# Canvas MCP — Copilot instructions (repo: canvas-mcp)

You are building the Canvas MCP server from scratch. Canvas is a
governed publication and audit layer for agent-built documents.
This repo is the MCP server only, for Copilot / Claude Code /
Cursor-style agents. Do not build the API, viewer, or CLI here —
those are separate repos. This repo is a thin tool layer over the
Canvas API: it adds no endpoints, no storage, and no business
logic of its own.

## Authentication: unauthenticated for now

- **Every API call this server makes is unauthenticated for now.**
  Do not build login, token storage, token refresh, session
  handling, or RBAC. The maintainer will wire authentication later
  and will say so explicitly when that changes.
- Send no credentials with any request. Do not read a token from
  the environment and attach it, and do not perform a token fetch,
  even if the API registry contains a `token_url`.
- Never return a secret, token, or credential in a tool result,
  and never log one. The registry stores URLs only.

## Stack and configuration

- Python MCP server (FastMCP-style, or the equivalent the
  maintainer already uses — keep one MCP framework, not two).
- API base URL from `CANVAS_API_URL` (default
  `http://127.0.0.1:8000`). Do not hardcode a production URL.
- Tool results are the API's responses, surfaced faithfully.
  Do not rewrite an API error into a different meaning, and do
  not invent a result when the API fails.
- Tests: pytest, with the HTTP client mocked. Never hit a live
  API from a unit test.

## Tools (build exactly these, same surface as the API)

Documents and versions (versions by NUMBER only):
- `list_documents` — `GET /v1/documents`.
- `get_document(document_id)` — latest version.
- `create_document(title, html)` — creates the document AND
  version 1 in one call. No draft argument, no change-summary
  argument.
- `publish_document(document_id, html)` — publishes the next
  version, body `{html}` only. No base-version argument, no
  change-summary argument.
- `list_versions(document_id)` — metadata, oldest first.
- `get_version(document_id, version_number)` — one version's
  metadata by number, not by id.
- `get_version_html(document_id, version_number)` — one version's
  raw HTML, byte-identical to what was published.

Shared state (document-scoped, not version-scoped):
- `get_document_state(document_id)` — all keys.
- `set_document_state(document_id, key, value)` — PUT one key;
  a null value deletes the key.
- `patch_document_state(document_id, patch)` — POST a patch;
  null values delete those keys.
- `delete_document_state(document_id, key)` — DELETE one key.
- Changing state never creates a version; publishing never
  resets state.

Registry:
- `register_api(app_name, base_url, token_url?, swagger_url?)`
  — fields are `app_name` / `base_url`, nullable `token_url` /
  `swagger_url`. No `name` / `api_url` / `scope` fields.
- `list_apis`, `get_api(app_name)`, `update_api(app_name, ...)`,
  `delete_api(app_name)`, `sync_apis_from_swagger(app_name)` —
  sync is owner-triggered, from the app's Swagger spec; removed
  endpoints are reported, never auto-deleted.
- API names are slugs: `^[a-z0-9][a-z0-9_\-]{0,63}$`. URLs must
  be https (http only for localhost dev).

## How agents should use these tools (put this in the MCP
## instructions the server serves, and in the repo README)

- Publish first, then view. A document's URL is durable; a new
  version does not change it.
- Read state before overwriting it: state survives versions, so
  a stale `set` can clobber a key another agent updated.
- Address versions by number. If a version is missing, it is a
  404 — do not fall back to latest and do not guess a version id.
- Live data in a document goes at view time via the viewer's
  bridge, never baked into published HTML, and never with a
  token or secret in the HTML.
- If a publish is rejected with `html_validation_failed`, fix
  the HTML (remove the secret / token URL / external resource /
  React import) and republish. A rejected publish stores nothing.

## Rules this server must not break

- No drafts: no draft create, save, or publish tools, no
  `?draft=1`.
- No approvals, no approval tools, no creator-approver checks.
- No version ids, no `base_version_id`, no 409 flow, no
  `change_summary`, no `byte_size`.
- No comments, reactions, mentions, notifications, grants, or
  sharing tools.
- No authentication, login, token verification, or RBAC tools.
  If the API does not have an operation, the MCP server does
  not invent one.

## Tests and acceptance

- Tests for: create (version 1), publish (next version, no
  base-version arg), get latest vs pinned version (404, no
  fallback), state set/patch/delete (null = delete), registry
  field names, and error passthrough.
- Acceptance, before calling the build done: from an MCP client
  against a running Canvas API, create a document, publish v2,
  fetch v1 and v2 (both correct), fetch a missing version (404),
  and set a state key (no new version created).

## Never reintroduce

Drafts, approvals, version ids, `base_version_id`, 409 flow,
`change_summary`, `byte_size`, `name`/`api_url`/`scope` registry
fields, comments, notifications, grants, authentication, login,
token verification, or any local storage of documents, versions,
or state.
