# Refactor report — `feat/refacto-clean-archi-2`

What changed between `main` and this branch, and why.

**55 commits · 107 files · +6880 / −3897**

| | before | after |
|---|---|---|
| `# Fixme:` markers | 131 (peak, after the code review) | **0** |
| `# Business rule:` markers | 0 | 8 — questions only the data owners can answer |
| Configuration variables | 7 | 31, all typed and documented |
| Python modules | 23, mostly flat | 58, grouped by responsibility |
| `docker compose up` | did not run at all | works from a clean clone |
| Linter | none | ruff, clean |

---

## 1. Architecture

The package was a flat `helpers/` drawer plus a `tools/` directory of prefixed files. Every module now
says what it holds.

**Before**
```
helpers/{es,es_search,rmes,schemas,logging}.py
middleware.py
tools/{insee_*,melodi_*,rmes_*,extras_send_feedback}.py
```

**After**
```
tools/<source>/       declare the MCP tools; wire, never compute
services/<source>/    orchestration and business logic
models/               tool schemas and result types
data/<source>/        static reference tables
lifespan/             builds the shared clients at startup
dependencies/         what a tool can be handed
errors/               the error contract and its translators
utils/, settings.py, instructions.py, logging.py, server.py
```

Key moves:

- **`helpers/` dismantled** — each file went to a module named for its subject (`0c639b8`).
- **`core/`, `infra/`, `config/` deleted** as junk drawers; their contents live at the package root or in
  a named package.
- **Static data grouped by source** (`b431717`) — `data/insee/`, `data/rmes/`.
- **One lifespan and one dependency module per source** (`bf8bca3`), so adding a source adds a file rather
  than editing one.
- **The error contract became a package** (`4d68c1d`) — `errors/` holds the type and the Elasticsearch
  translator, which had been sitting in `services/` despite orchestrating nothing.
- **The package root earned a membership rule**: it holds only what `server.py` needs to boot.

## 2. FastMCP 4 adoption

The version had been bumped without adopting the APIs.

- **Dependency injection** replaced service-locator lookups in every tool (`efa39aa`, `8c71e83`, `b7d1e14`).
  Tools declare what they need; `Depends` resolves it per request and hides it from the LLM schema.
- **Registration wrappers removed** — every tool is a plain function added with `mcp.add_tool`.
- **Built-in rate limiting** replaced a hand-rolled middleware, and the `limits` dependency went with it.
- **Built-in host protection** replaced hand-wired `TrustedHostMiddleware` (`3d21279`).
- **`mask_error_details=True`** so unexpected exceptions stop leaking their message to clients.
- **Tool descriptions moved into docstrings**, which FastMCP parses for both the tool and its parameters.

## 3. Bugs fixed

The substantive ones, each reproduced before being fixed.

### Errors that never reached the caller

- **Elasticsearch `ApiError` escaped the failure boundary entirely** in both insee and melodi — a missing
  index, a 400, a 401/403 or a 5xx surfaced as an internal error with no guidance. `ApiError` does not
  subclass `TransportError`; catching one never caught the other (`974cc5a`).
- **`search_insee_chiffrecle` reported the wrong backend** in its failure message — a copy-paste.
- **MELODI answers HTTP 400 for an unknown dataset, column and modality alike**; the message only ever
  suggested checking modality codes. All three bodies were confirmed live, and the message now names every
  remedy.

### Silent data loss

- **A query whose only `LIMIT` sat in a subquery went unbounded** (`24acd77`). The check matched `LIMIT`
  anywhere, so a subquery's own limit — or the word inside a string literal — counted as the caller's.
- **One malformed observation failed the whole batch** (`b5fa91d`). An observation with a null `dimensions`
  raised `AttributeError`, which is not a `ToolError`, so the caller lost every row over one.
- **The handshake instructions named tools that were not registered** (`22e92a2`). Sections cross-reference
  each other, so disabling a family left the model being told to call tools that did not exist.
- **`send_feedback` had been silently dropped** (`310f19c`) — it was registered until a commit removed the
  `else` branch that carried it. It was the only tool registered exclusively there, so nobody noticed, while
  `SKILL.md` kept instructing clients to call it.

### Concurrency and lifecycle

- **A thundering-herd race on the RMES graph cache** — a module global with no lock. Replaced by instance
  state with an `asyncio.Lock` and a double freshness check; verified 10 concurrent callers produce one
  execution.
- **The server could not start in rmes-only mode** (`4a28e5b`) — `ES_HOST` was required unconditionally,
  though only insee and melodi search Elasticsearch.
- **One tool's limits governed another's queries** (`f0b7f94`) — `run_rmes_sparql`'s schema bound was applied
  inside the shared execute path, silently capping the graph listing at 60s regardless of its own documented
  setting, and `describe_rmes_resource` drew its budget from a tool it does not expose.

## 4. Security

- **Every caller shared one rate-limit bucket** (`68d149c`). Behind a Kubernetes ingress, `TRUSTED_PROXY_HOSTS`
  defaulted to `127.0.0.1`, so uvicorn ignored `X-Forwarded-For` and every client looked like the ingress.
- **The host guard approved everyone** (`3d21279`) — `allowed_hosts=["*"]` with `host_origin_protection="auto"`,
  while `allowed_origins` was doing the rejecting and was not configurable.
- **The Elasticsearch host leaked to clients** in exception messages under `max_retries=2`, which is the
  production setting. Only the exception type is quoted now; the full cause stays in the server log.
- **SPARQL injection through a resource URI** (`6d830f7`). `describe_rmes_resource` interpolated the URI into
  `<...>`; a `>` closed the brackets and the rest ran as query text. Both parameters are now checked against
  the IRI grammar, which forbids those characters anyway.
- **Unbounded input** — no cap on how many documents one call could request (`5fb6451`), and no length bound
  on feedback. Both are schema bounds now, so the model is told the limit rather than discovering it.

## 5. Error handling

- **A single error type and a closed vocabulary** (`4ae8b78`). `ErrorCode` was a `Literal` — a promise to a
  type checker that nothing enforced, so `AppToolError('TOTALLY_MADE_UP', ...)` was accepted silently. It is
  a `StrEnum` now; a typo fails at the reference.
- **`UNKNOWN` became `INTERNAL_ERROR`** — the former advertised poor error handling rather than naming a fault.
- **Translation happens once, at the boundary owning the dependency**, in `errors/`.
- **Error messages are the contract**: every one names the backend, the failure, and the next step. Message
  text was diffed byte-for-byte across the refactor so the contract did not drift.

## 6. Configuration

- **7 variables became 31**, all typed in `settings.py`, all documented in `.env.example`, and verified in
  sync both directions.
- **No magic numbers left in the code paths that matter** — timeouts, retries, index names, budgets and
  limits are settings.
- **Settings fail at startup, not on first use** — a validator rejects a configuration that cannot work.
- **Schema bounds stayed out of settings deliberately** (`9e125ac`). They bound the published tool schema, so
  an env-driven value would advertise a different contract per deployment.
- **Renames pending release notes**: `ES_INDEX_PRODUITS` → `ES_INDEX_PUBLICATIONS`,
  `RMES_ENDPOINT` → `RMES_SPARQL_ENDPOINT_URL`, `ENABLE_INSEEFR_TOOLS` → `ENABLE_INSEE_TOOLS`.

## 7. Performance

- **Documents are fetched concurrently** (`abfbbd4`) — a batch took the sum of its URLs; five 0.3s fetches
  went from 1.50s to 0.32s.
- **Rendering moved off the event loop** (`7a2e9cd`). Turning a page into markdown costs 80–1000 ms of CPU,
  and it ran on the loop: during a batch the server served *nothing else* — a probe scheduled every 10 ms got
  zero turns. Now a worker thread; the batch costs ~7% more, the server stays responsive.

## 8. Build and tooling

- **ruff adopted** for linting and formatting (`6030832`), with `FBT003` guarding the call-site convention
  that replaced keyword-only markers (`26bdf59`).
- **The image build hardened** (`9508aa3`) — a `.dockerignore` (the build context had been shipping `.venv`
  and `.git`), uv pinned instead of `:latest`, `--locked` instead of `--frozen` so a stale lock fails the
  build rather than silently omitting a dependency, plus a healthcheck, OCI labels and cache mounts.
- **The whole stack runs with one command** (`20e8456`). Compose previously referenced an image nobody built,
  ran no Elasticsearch though the tools require one, expected a hand-created network, and read an env file
  that does not exist. It now builds the server, starts Elasticsearch with the INSEE indexes, restores the
  snapshot, and waits for each step before the next.
- **Elasticsearch runs native on arm64 and amd64** — the published image is amd64-only, so the snapshot is
  copied into the official multi-arch base rather than the image being run under emulation.

## 9. Conventions

- **Tools, parameters and schemas named after what they are** (`cdf44df`) — a breaking rename, done once.
- **English throughout the code**; French remains only where it is data (insee.fr CSS classes, RMES messages).
- **A convention file per concern** under `.claude/rules/` — python, errors, logging, git — updated whenever a
  decision contradicted them, so the harness and the code agree.
- **Attribution forbidden in commit messages**, and existing trailers stripped from history (`396ea7e`).

---

## Deliberately left open

Not oversights. Each is recorded in the code where it matters.

**8 `# Business rule:` markers** — questions only whoever owns the search and data semantics can answer:

- Homepage indicators are frozen literals; nothing refreshes them.
- insee.fr theme ids are transcribed by hand and nothing here can verify them.
- An unrecognised geo level, theme or subtheme drops its filter silently and broadens the search.
- MELODI observations are fetched whole and filtered locally: the API's own year filter matches only periods
  *starting* on that date, so it returns the annual row and January but not August. Filtering upstream would
  silently lose most of a monthly dataset — verified on `DS_DECES_MORTALITE_SERIES`.

**Known gaps**

- `k8s/3_mcp_deploy.yaml` declares no readiness or liveness probe. Kubernetes ignores Docker's `HEALTHCHECK`,
  so the pod is considered ready before the lifespan has opened its clients.
- No Elasticsearch credentials are supported — only host, TLS verification, timeouts and retries. Fine for the
  current deployment; a secured cluster would need a settings addition.
- `README.md` and `SKILL.md` describe the pre-refactor code and are scheduled for regeneration.
- The test suite does not collect; it is auto-generated, unreviewed, and slated for a single pass of its own.
