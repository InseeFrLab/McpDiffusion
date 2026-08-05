# McpDiffusion

> **BETA** — This project is in BETA. It should not be considered a finished nor an official product supported by INSEE.

MCPDiffusion is a MCP server that exposes INSEE (French National Institute of Statistics and Economic Studies) public data to Large Language Models. It combines three INSEE data sources behind a single [Model Context Protocol](https://modelcontextprotocol.io/) endpoint so that an LLM client can discover and call them as native tools.

Server's URL : https://mcpdiffusion.lab.sspcloud.fr/mcp

## Table of Contents

- [Features](#features)
- [Data Sources](#data-sources)
- [Architecture](#architecture)
- [Available Tools](#available-tools)
- [LLM Usage Guide](#llm-usage-guide)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Connecting an MCP Client](#connecting-an-mcp-client)
- [Project Structure](#project-structure)
- [Limitations](#limitations)
- [Security Notice](#security-notice)
- [Contributing](#contributing)
- [License](#license)

## Features

- A single MCP endpoint exposing INSEE publications, datasets and concept definitions.
- Tools auto-registered through [FastMCP](https://github.com/jlowin/fastmcp).
- HTTP transport (default port `8000`) compatible with any MCP-capable client.
- Docker image published automatically on every push to `main`.
- Structured logging (`mcp.main`, `mcp.tools`) and per-tool call tracing.

## Data Sources

| Source | Type | Purpose |
|---|---|---|
| **RMES** | SPARQL endpoint at `https://rdf.insee.fr/sparql` | INSEE statistical ontology: vocabulary, concept definitions (SKOS/XKOS). Works **without** any local dependency. |
| **MELODI** | REST API + ElasticSearch index | INSEE data catalogue: search datasets, list columns, fetch filtered observations. |
| **insee.fr** | HTTP scraping | Official INSEE publications, *Informations rapides*, and the homepage key indicators. |

External references:
- Publications: https://www.insee.fr/en/statistiques
- Datasets: https://catalogue-donnees.insee.fr/en/catalogue/recherche
- Definitions: https://www.insee.fr/en/metadonnees/definitions

## Architecture

```
┌──────────────────────────┐
│  MCP client              │
│  (Claude Code, Cursor,   │
│   VS Code, …)            │
└────────────┬─────────────┘
             │  MCP / HTTP (port 8000)
             ▼
┌──────────────────────────────────────────────┐
│  FastMCP server  (mcpdiffusion/server.py)    │
│  ┌────────────────────────────────────────┐  │
│  │  tools/__init__.py — register_tools()  │  │
│  └────────────────────────────────────────┘  │
│         │              │             │       │
│         ▼              ▼             ▼       │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│   │  INSEEFR │   │  MELODI  │   │   RMES   │ │
│   │   _*     │   │   _*     │   │  _*      │ │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘ │
└────────┼──────────────┼──────────────┼───────┘
         │              │              │
         │              │              ▼
         │              │       ┌─────────────────┐
         │              │       │  rdf.insee.fr   │
         │              │       │  (SPARQL)       │
         │              │       └─────────────────┘
         ▼              ▼
   ┌────────────┐  ┌────────────┐
   │  insee.fr  │  │ Elastic    │
   │  (HTTP)    │  │ Search     │
   └────────────┘  └────────────┘
```

The server boots, loads environment variables, calls `register_tools(mcp)` to attach every tool exposed in `mcpdiffusion/tools/`, and then runs the FastMCP HTTP application under Uvicorn.

## Available Tools

| Tool | Source | Description |
|---|---|---|
| `get_insee_homepage` | insee.fr | Retrieve the latest key indicators published on the INSEE homepage (inflation, unemployment, GDP, …). Prefer this for generic, up-to-date questions. |
| `search_insee_documents` | insee.fr | Search the INSEE catalogue of detailed publications (Insee Première, Insee Analyses, Dossiers, Références, Chiffres-clés, …). |
| `get_insee_document` | insee.fr | Fetch and parse a specific INSEE publication from a known URL (`/fr/statistiques/<id>`). |
| `search_insee_conjoncture` | insee.fr | Search the *Informations rapides* (rapid releases) index by topic, date and geography. |
| `search_insee_chiffreclef` | insee.fr | Search key figures and synthetic statistics (population, regional comparisons, simple factual questions). |
| `search_melodi_datasets` | MELODI | Search the Melodi dataset catalogue with a natural-language French query. |
| `search_melodi_modalities` | MELODI | Given a dataset and column identifiers, rank the most relevant modality codes/labels for a free-text query. |
| `get_melodi_observations` | MELODI | Retrieve filtered observations from a Melodi dataset (dimensions, attributes, numeric measure with unit). |
| `RMES_list_graphs` | RMES | List available named graphs in the INSEE semantic database, grouped by category (nomenclatures, concepts, operations, …). Use this first to discover the graph structure. |
| `RMES_describe_resource` | RMES | Retrieve all properties (predicate → value) of a specific RDF resource identified by its URI. Useful for exploring concept definitions or classification hierarchies. |
| `RMES_run_sparql` | RMES | Run a SPARQL query against the INSEE semantic graph (concept definitions, code lists, metadata). The only tool that works **without** an Elasticsearch instance. |
| `send_feedback` | Extras | Submit structured feedback about tool behavior, bugs, or suggestions for improvement. Appends timestamped entries to the feedback log. |

## LLM Usage Guide

For detailed guidance on how to effectively use these tools as a Large Language Model, see [**SKILL.md**](SKILL.md). It includes:

- Tool selection decision trees
- Workflow patterns for each data source
- Common pitfalls and how to avoid them
- SPARQL query templates
- MELODI three-step workflow (search → modalities → observations)

The skill file is designed to be loaded into your context when working with INSEE data through this MCP server.

## Prerequisites

- **Python 3.12** (matches the Dockerfile base image)
- A running **Elasticsearch** instance reachable from the server (required for all `MELODI_*` and `INSEEFR_*` tools)
- Internet access to `insee.fr` and `rdf.insee.fr`
- *(Optional)* **Docker** if you want to run the server in a container

> Without Elasticsearch, only `RMES_run_sparql` is functional.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/InseeFrLab/McpDiffusion.git
cd mcp_diffusion
```

### 2. Configure environment

```bash
cp mcpdiffusion/.env.example mcpdiffusion/.env
# then edit mcpdiffusion/.env (see Configuration)
```

### 3. Install dependencies

```bash
pip install -r mcpdiffusion/requirements.txt
```

### 4. (Alternative) Build the Docker image

```bash
docker build -t mcp-insee .
```

## Configuration

All settings live in `mcpdiffusion/.env`:

| Variable | Default | Description |
|---|---|---|
| `MCP_HOST` | `0.0.0.0` | Bind address. Use `127.0.0.1` for local development. |
| `MCP_PORT` | `8000` | HTTP port the FastMCP server listens on. |
| `ES_HOST` | `http://elasticsearch:9200` | Elasticsearch URL when running in Docker. |
| `ES_HOST_LOCAL` | `http://localhost:9200` | Elasticsearch URL when running on the host. |

Additional optional variable: `LOG_LEVEL` (default `INFO`).

## Running the Server

### Local

```bash
python3 mcpdiffusion/server.py
```

The server listens on `http://$MCP_HOST:$MCP_PORT` (defaults to `http://0.0.0.0:8000`).

### Docker

```bash
docker run --rm \
  -p 8000:8000 \
  --env-file mcpdiffusion/.env \
  mcp-insee
```

Health check:

```bash
curl -i http://localhost:8000/
```

## Connecting an MCP Client

The server speaks MCP over HTTP. Any MCP-compatible client can be pointed at it. Below are examples for the most common clients.

### Claude Code (CLI)

Add the server globally:

```bash
claude mcp add --transport http mcp-insee http://localhost:8000
```

…or per-project, in `.mcp.json` at the repository root:

```json
{
  "mcpServers": {
    "mcp-insee": {
      "type": "http",
      "url": "http://localhost:8000"
    }
  }
}
```

Then start a Claude Code session in this directory. The tools listed in [Available Tools](#available-tools) will appear automatically.

### Claude Desktop

Edit `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcp-insee": {
      "type": "http",
      "url": "http://localhost:8000"
    }
  }
}
```

Restart Claude Desktop; the tools will be available under the 🔌 menu.

### Other MCP clients (Cursor, VS Code Continue, …)

Any client supporting the MCP HTTP transport can be configured the same way:

```json
{
  "mcpServers": {
    "mcp-insee": {
      "url": "http://localhost:8000"
    }
  }
}
```

## Project Structure

```
mcp_diffusion/
├── Dockerfile
├── README.md
├── LICENSE
└── mcpdiffusion/
    ├── server.py                # FastMCP entrypoint (Uvicorn + register_tools)
    ├── requirements.txt
    ├── .env.example
    ├── helpers/
    │   └── logging.py           # logging config + @log_tool decorator
    └── tools/
        ├── __init__.py          # register_tools(): enable/disable tools here
        ├── env.py               # tool metadata + theme/geo dictionaries
        ├── INSEEFR_get_homepage.py
        ├── INSEEFR_search_documents.py
        ├── INSEEFR_get_documents.py
        ├── INSEEFR_get_conjoncture.py
        ├── MELODI_search_dataset.py
        ├── MELODI_get_columns.py
        ├── MELODI_get_dataset.py
        └── RMES_search_graph.py
```

Each tool lives in its own file and is registered by `tools/__init__.py`. To **disable** a tool, comment out its import and the corresponding call in `register_tools()`.

## Limitations

- **BETA software.** APIs, tool schemas, and configuration may change without notice.
- **ElasticSearch is not public.** Most tools depend on a private ElasticSearch index. Only `RMES_run_sparql` works without it.
- The *RMES* tool accepts raw SPARQL — model clients must be capable of generating well-formed queries.
- Tool schemas and category names are currently a mix of French and English (mirrors the INSEE source data).
- The GitHub Actions workflow pushes a Docker image on every push to `main`; the image name is configured via the `DOCKER_USERNAME` repository variable.

## Security Notice

The shipped configuration is intentionally permissive for local testing:

- `server.py` disables DNS rebinding protection and uses `TrustedHostMiddleware` with `allowed_hosts=["*"]` (flagged with `# remove before flight`).
- Uvicorn is started with `forwarded_allow_ips="*"`.

**Before deploying anywhere reachable from the internet, harden these settings** — restrict `allowed_hosts`, re-enable rebinding protection, and limit `forwarded_allow_ips` to your reverse proxy.

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feat/my-tool`).
3. Add or modify a tool in `mcpdiffusion/tools/` (one tool per file).
4. Register it in `mcpdiffusion/tools/__init__.py` inside `register_tools()`.
5. Run the server locally and exercise the new tool with an MCP client.
6. Open a Pull Request.

Issues and PRs are welcome — this is a BETA project.

## License

Released under the **Apache License 2.0**. See [LICENSE](LICENSE) for the full text.