# Copilot instructions for agent-docs

Copy this file to `.github/copilot-instructions.md` in the project where
you build agent-docs pages. VS Code Copilot reads that file automatically.
It is guidance for the agent, not a security boundary: the viewer bridge
still keeps tokens out of documents (see "Live data" below).

## What agent-docs is

- A publish / view / version-history system for documents. The React UI
  is viewer chrome only. A document is ONE self-contained HTML file.
- Documents are plain HTML + CSS + JavaScript. Never put React, JSX,
  or a framework build step inside a document. Inline CSS and JS, or
  inline SVG / Mermaid, are fine. There is no size cap on a
  document in agent-docs: HTML is stored as-is, however large.
- The viewer renders a document in a sandboxed iframe
  (`sandbox="allow-scripts"`, no `allow-same-origin`). Document code
  cannot reach the viewer's origin, cookies, or storage.

## Workflow — always in this order

1. `list_apis` first. If the app the user named is not registered,
   register it (`register_api` with name, base URL, token URL) or sync
   it (`sync_apis_from_swagger`) before building anything.
2. `list_documents` to check whether the page already exists.
3. Build the HTML file locally.
4. Test it as a draft before publishing: new page,
   `create_draft_document` (title + HTML); existing page,
   `save_draft`. A draft creates no version — view it on the
   actual viewer link (`?doc=<id>&draft=1`) with live data,
   state, and navigation working, share that link for review,
   and only then `publish_draft`. Direct publish with
   `create_document` / `publish_document` (latest version as
   `base_version_id`) is for when the page is already known good.
5. On a 409 `version_conflict`, do NOT retry the same publish.
   Re-fetch the document, take its current version id as the new base,
   and publish again.
6. Report back the document title, document id, and version number.
   Never report a publish as done before the tool call succeeds.

## Publish-time validation — the API enforces what this file asks

Instructions alone are not enforcement. The API validates every
publish (create and new version, MCP and CLI alike) before
anything is stored, and rejects with 400 `html_validation_failed`
plus specific violation codes: `secret_detected`, `token_url_in_html`,
`direct_fetch`, `external_resource`, `react_import`. A rejected
publish stores nothing and changes no version history. When a
publish is rejected, fix the exact violation named — remove the
secret or token URL, replace a direct fetch with `apiFetch`,
inline an external resource — and publish again. Never work
around a rejection by publishing through another route; every
route runs the same validation.

## Live data — the most important rule

- A document MUST load live data only through the viewer bridge:

  ```js
  const res = await window.agentdocs.apiFetch("refdp", "/reports");
  // res is { status, data } — never a token, never a raw response object.
  ```

- Never `fetch()` a source API directly from document code. The
  document runs in a sandboxed iframe and has no credentials.
- NEVER put a token, token URL, API key, secret, or credential in
  published HTML — not in code, comments, hidden fields, or data
  attributes. Tokens live in the API registry only, as URLs, and are
  fetched at view time by the viewer chrome, per viewer, per endpoint.
- A 403 on one section must NOT kill the whole page. Fetch sections
  independently (e.g. `Promise.allSettled`), render each section on
  its own, and show a plain message ("No access to this section")
  where a call failed. A 401 is retried once by the bridge.
- Bake data into the HTML only if the user explicitly asks for a
  snapshot. Otherwise the page is live-at-view: it shows current data
  every time it is opened, and version history is template history,
  not data history.

## APIs and Swagger sync

- An app has a short name (e.g. `refdp`). A document calls it by that
  name plus a path: `apiFetch("refdp", "/risks")`, not by pasting a
  base URL into the page.
- After a Swagger doc changes, run `sync_apis_from_swagger(app, url)`.
  The first run stores the Swagger URL in the app config; later runs
  need only the app name. Report added / removed / unchanged endpoints.
  Removed endpoints are reported, never auto-deleted: do not remove
  them from the registry unless the user explicitly says to.
- A Swagger doc gives base URL and paths. It gives a token URL only
  if its oauth2 security scheme carries one; otherwise keep the
  existing token URL. Never invent a token URL from paths.

## Shared state

- `window.agentdocs.kv` is document-scoped key/value state for things
  like a filter or toggle: `kv.get`, `kv.all`, `kv.set`, `kv.delete`,
  `kv.patch`. Values are JSON, keys max 128 chars, values max 64 KiB.
- State survives versions and never creates a version. `null` deletes
  a key. State does NOT carry across navigation to another document:
  each document has its own state.

## Navigation

- Inside one page, build tabs / sections / a sidebar in plain HTML
  and JS. Each section calls its own `apiFetch` path.
- Between pages, use the viewer nav bar, or link from inside a
  document with:

  ```js
  window.agentdocs.navigate("doc_...");
  // or: <a data-agentdocs-doc="doc_...">Reports</a>
  ```

  Never use a plain `<a href>` to another agent-docs page: inside the
  sandboxed iframe it would navigate the iframe itself and lose the
  viewer chrome. A page is also deep-linkable as `?doc=<document id>`.
- When building a multi-page site, publish one document per page,
  in nav order, and tell the user the page titles in that order.

## What agent-docs does NOT have

Do not promise or invent: comments, reactions, mentions,
notifications, sharing/grants UI, approvals UI, real-time co-editing,
search, or live presence. If the user asks for one of those, say it is
out of scope and ask what they want instead. Do not build auth: Entra
OBO / hantweb wiring belongs to the maintainer, and the viewer token
plumbing is a placeholder until they wire it.
