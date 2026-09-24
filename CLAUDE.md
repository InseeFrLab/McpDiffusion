# Project instructions

This file may be updated during the refactoring process.

## What this repo is

McpDiffusion is an **MCP server that exposes INSEE public data to LLM clients**.
It puts three INSEE sources behind one HTTP MCP endpoint:

| Source   | Access                                   | Content                                                                |
|----------|------------------------------------------|------------------------------------------------------------------------|
| insee.fr | Elasticsearch index + live HTML scraping | publications, *Informations rapides*, key figures, homepage indicators |
| MELODI   | Elasticsearch index + REST API           | dataset catalogue and observations                                     |
| RMES     | SPARQL (`rdf.insee.fr`)                  | definitions, classifications, metadata (no figures)                    |

Single Python package under `src/mcpdiffusion/`, managed with `uv`, built on **FastMCP 4**.
`docs/project.md` is the long-form overview.

Elasticsearch is required for the insee.fr and MELODI tools; only RMES works without it. This repo contains
no indexing code — it only reads. The index ships as a prebuilt snapshot from outside the repo.

`SKILL.md` is a usage guide written **for the LLM client**, not for maintainers. It describes tool names and
workflows, so any change to those makes it wrong — tell me when that happens. It gets regenerated from the
code once the refactor settles, so do not patch it as you go.

## Current mission

Make this project production-ready.

- **Adopt the FastMCP 4 APIs, not just the version.**
    - The version bump has been done. It does not mean the code is idiomatic of the v4 patterns
    - Apply more recent and adapted patterns when possible and notify me previously
    - **Review the MCP layer against the official docs** — tool declaration, descriptions, lifespan, context,
      dependency injection, middleware, error handling. Some of it may not follow current FastMCP recommendations.
- **When you see overengineering** — something hand-rolled that FastMCP already provides — notify, plan,
  and propose an accurate correction. Do not silently rewrite it. This applies not only for fastmcp but at the whole
  project source scale
- **Fix the identified issues.** Bugs and review comments are marked `# Fixme:` in the source. Also fix any
  other bug you find, and say what you found.

Verified against `fastmcp-docs` — these are confirmed, not guesses:

- **Tool descriptions belong in docstrings.** FastMCP parses the docstring for both the tool description and
  every parameter description (Google/NumPy/Sphinx). `Annotated[x, "..."]` and `Field(description=...)` take
  precedence, so adoption can be incremental. `config/tool_metadata.py` is largely redundant.
  → `/servers/tools#docstring-descriptions`
- **The rate limiter is built in.** `RateLimitingMiddleware` (token bucket) and
  `SlidingWindowRateLimitingMiddleware` (precise window, no burst) both accept `get_client_id` for per-client
  keying. `core/middleware.py` reimplements this, and the `limits` dependency goes with it.
  → `/servers/middleware#rate-limiting`
- **Host protection is built in.** `mcp.http_app(host_origin_protection=True, allowed_hosts=[...],
  allowed_origins=[...])` replaces the hand-wired `TrustedHostMiddleware` in `server.py`.
  → `/deployment/http.mdx`
- **`mcp.http_app()` is current.** It also takes `middleware=` for ASGI middleware. No change needed.
- **`ctx.lifespan_context` is current** — the documented way to reach shared clients, exactly as `infra/` does
  it. `fastmcp.dependencies.Depends` is a *different* tool (hiding parameters from the LLM schema), not a
  replacement. The `# Fixme:` about those accessors being untyped still stands; "four files go away" does not.
  → `/servers/lifespan#accessing-lifespan-context`

## Main commands

All commands run from the repo root.

```bash
uv sync                                       # install (dev deps included)
uv run python -m mcpdiffusion.server          # run the server locally, needs ES_HOST
uv run pytest -q                              # test suite — do not trust it, see Hard rules

cp .env.example .env                          # once, before the first compose run
docker compose up --build                     # Elasticsearch + data + server + MCP Inspector
```

## Hard rules

- **The `fastmcp-docs` MCP server is connected and available right now. Use it.** Never answer a FastMCP
  question, and never write or change FastMCP code, from memory. v4 is recent and moved things, so a
  remembered API is more likely wrong than right. Look it up first, every time — including when you are
  confident. If a lookup contradicts what you were about to write, the docs win.
- **The markdown documentation is out of date. Never base a change on it.** `README.md` and `SKILL.md`
  describe the pre-refactor code — wrong layout, wrong tool count, wrong tool names. `docs/project.md` is
  the most accurate but still not authoritative. **The code is the only source of truth.** Read a `.md` to
  learn intent, never to learn behaviour. They get regenerated once the refactor settles; until then report
  a mismatch, never silently follow it.
- **All configuration is typed in `config/settings.py`.** No magic numbers, URLs, timeouts or limits in the
  code, and nothing read from the environment anywhere else.
- **A setting is not done until the documented configuration surface changes in the same commit.** The example
  env file is the only description of what this server can be configured with — how the values actually reach
  the process (shell, compose `env_file`, k8s `env:`) does not change that.
- **Keep every place that names a setting in sync**: the example env file, the env file
  `docker-compose.yml` expects, and the `env:` block in `k8s/`. A variable set in a manifest that
  `Settings` no longer reads is a bug, not leftovers. Touching `k8s/` for this is expected — it is the
  exception to the rule below.
- Ask before adding a dependency, a new tool, or a new data source.
- Never commit to `src/mcpdiffusion/feedback/feedback.md`. It is user-submitted content.
- Do not touch `k8s/` or `.github/workflows/` unless the task is about deployment.
- Do not fix a `# Fixme:` by deleting the comment without changing the code. If the comment turns out to be
  wrong or irrelevant, say so and ask before removing it.
- **Two markers, two meanings.** `# Fixme:` is ours to fix. `# Business rule:` marks a question only whoever
  owns the search and data semantics can answer — preserve the current behaviour, flag it, and never decide
  it yourself. Reclassifying one as the other needs my agreement.
- **Do not rely on the existing tests.** They were auto-generated and never reviewed. Verify your own work
  (see below).
- There is no linter, formatter or type checker configured. Do not assume a command exists; propose one first.

## Application layer

**The current code is not a reference. Do not copy a pattern just because you found it in the repo** — several
files predate any convention.

Targeted conventions, to be confirmed or infirmed as we go. Plan and propose better ones freely:

- `tools/` — declares the MCP tools. Wires, does not compute.
- `services/` — orchestration and business logic.
- `repositories/` — data access: Elasticsearch queries, HTTP calls, SPARQL. *(proposed; does not exist yet —
  these currently live in `services/`)*
- `clients/` — builds and provides the shared Elasticsearch / HTTP / SPARQL clients. *(currently `infra/`;
  the accessors stay — `ctx.lifespan_context` is the documented API — but they need real typing)*
- `config/` — settings only. Clients are live objects with a lifecycle; settings are static values. Keep them apart.
- `core/` — cross-cutting concerns that belong to no single source: error types, logging setup, middleware.

This section gets adjusted as we settle on FastMCP patterns and conventions.

## Verifying a change

No test imports `server.py`, so the app, middlewares, lifespan and tool registration are never exercised by
the suite. A green suite does not mean the server boots:

```bash
ES_HOST=http://localhost:9200 uv run python -c "
import asyncio
from fastmcp import Client
from mcpdiffusion import server
async def main():
    async with Client(server.mcp) as c:
        print([t.name for t in await c.list_tools()])
asyncio.run(main())"
```

A pass prints the tool list **and exits 0**. `FastMCP.get_tools()` no longer exists in v4 — list tools
through an in-memory `Client` as above.
