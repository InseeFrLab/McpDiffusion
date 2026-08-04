---
name: insee-mcp-tools
description: "Use when the user asks for French statistics, INSEE data, economic indicators, publications, classification codes (NAF, PCS, COICOP), or needs to query French demographic/economic datasets. Routes to insee.fr (publications), MELODI (datasets), or RMES (SPARQL) based on data type."
version: 1.0.0
author: mirlon382
license: Apache-2.0
metadata:
  hermes:
    tags: [mcp, statistics, france, insee, sparql, data, publications]
    related_skills: []
---

# INSEE MCP Server - Tool Usage Guide

## Overview

This skill guides effective use of the INSEE MCP server, which exposes French National Institute of Statistics (INSEE) data through three complementary data sources: **insee.fr** (publications), **MELODI** (datasets), and **RMES** (semantic graph/SPARQL).

**Core principle**: Always start with discovery tools before making specific queries. INSEE's data is vast and highly structured — guessing dataset IDs, URLs, or SPARQL patterns will fail.

---

## When to Use

**Use this skill when**:
- User asks about French statistics (inflation, unemployment, GDP, population, etc.)
- User needs INSEE publications, reports, or analyses
- User wants raw statistical datasets or time series from France
- User needs concept definitions, classifications, or metadata (NAF codes, PCS, COICOP, etc.)
- User mentions French nomenclatures or asks "what is X" for a statistical concept
- User asks about demographic or economic data specific to France or French regions
- User wants to query the INSEE semantic graph or RDF data

## When NOT to Use

**Do not use this skill for**:
- Statistics from other countries (Germany, US, EU-wide Eurostat, etc.)
- Generic data analysis, CSV manipulation, or database queries unrelated to INSEE
- PDF/document processing that isn't fetching INSEE publications
- Visualization or dashboard creation (unless specifically about displaying INSEE data)
- Debugging SPARQL queries for non-INSEE endpoints (DBpedia, Wikidata, etc.)
- General economic theory or statistical methodology questions
- Tools or APIs that aren't the INSEE MCP server

---

## Tool Routing Decision Table

Use this table to select the correct tool family for any query:

| Query Type | Data Source | Primary Tool | Workflow |
|------------|-------------|--------------|----------|
| **Latest headline indicators** (inflation, GDP, unemployment rate) | insee.fr | `get_insee_homepage` | Direct call |
| **Recent rapid releases** (monthly/quarterly updates) | insee.fr | `search_insee_conjoncture` | Search → Fetch |
| **In-depth publications** (analyses, reports, methodologies) | insee.fr | `search_insee_documents` | Search → Fetch |
| **Key figures** (population, simple factual stats) | insee.fr | `search_insee_chiffreclef` | Search → Fetch |
| **Raw statistical data** (time series, counts, filtered tables) | MELODI | `search_melodi_datasets` | 3-step workflow (see below) |
| **Concept definitions** (what is inflation, unemployment) | RMES | `RMES_list_graphs` → `RMES_run_sparql` | Discover → Query |
| **Classification codes** (NAF, PCS, COICOP, CJ) | RMES | `RMES_list_graphs` → `RMES_run_sparql` | Discover → Query |
| **Metadata about surveys** (statistical operations) | RMES | `RMES_list_graphs` → `RMES_run_sparql` | Discover → Query |
| **Geographic codes** (COG, communes, departments) | RMES | `RMES_list_graphs` → `RMES_run_sparql` | Discover → Query |
| **Quality reports** (per statistical operation) | RMES | `RMES_list_graphs` → `RMES_run_sparql` | Discover → Query |

### Decision Flowchart

```
START: User query about French statistics
  │
  ├─ Is it a LATEST indicator (today's inflation, current unemployment)?
  │   └─ YES → get_insee_homepage
  │
  ├─ Is it a PUBLICATION or REPORT (analysis, methodology, detailed study)?
  │   └─ YES → search_insee_documents OR search_insee_conjoncture
  │
  ├─ Is it RAW DATA (time series, counts, specific filtered table)?
  │   └─ YES → search_melodi_datasets (3-step workflow)
  │
  ├─ Is it a DEFINITION, CLASSIFICATION, or METADATA?
  │   └─ YES → RMES_list_graphs → RMES_run_sparql
  │
  └─ UNSURE?
      └─ Start with get_insee_homepage, then ask user to clarify
```

---

## Tool Families: Detailed Workflows

### 1. insee.fr Tools (Publications and Headlines)

**When to use**: You need recent publications, official analyses, methodological documents, or the latest headline indicators.

**Tools**:
- `get_insee_homepage` — Latest key indicators (inflation, unemployment, GDP, etc.)
- `search_insee_documents` — Search the full publication catalogue
- `get_insee_document` — Fetch a specific publication by URL
- `search_insee_conjoncture` — Search "Informations rapides" (rapid releases)
- `search_insee_chiffreclef` — Search key figures and synthetic statistics

**Workflow**:
```
1. get_insee_homepage → Check if the answer is in the latest indicators
2. search_insee_documents OR search_insee_conjoncture → Find relevant publications
3. get_insee_document → Fetch the full text of promising results
```

**Critical rules**:
- Publications are in **French**. Use French keywords in queries (e.g., "chômage" not "unemployment")
- `get_insee_document` requires a URL from a previous search — **never guess URLs**
- Distinguish between `search_insee_documents` (deep analyses) and `search_insee_conjoncture` (rapid updates)

**Example**:
```
User: "What's the current unemployment rate in France?"
→ get_insee_homepage (check latest indicators first)
→ If not found: search_insee_conjoncture with query="chômage taux France"
→ get_insee_document on the most recent result
```

---

### 2. MELODI Tools (Statistical Datasets)

**When to use**: You need raw statistical data — time series, demographic tables, economic indicators with specific filters.

**Tools**:
- `search_melodi_datasets` — Find datasets by French natural-language query
- `search_melodi_modalities` — Discover column codes and valid filter values
- `get_melodi_observations` — Fetch filtered data rows

**Three-step workflow (MUST follow this order)**:
```
1. search_melodi_datasets → Get dataset_id and column_ids
2. search_melodi_modalities → Get valid modality codes for filtering
3. get_melodi_observations → Fetch data with correct filters
```

**Critical rules**:
- **Never skip steps**. Dataset IDs and modality codes are opaque identifiers — you cannot guess them
- Queries must be in **French with rich synonyms**: "prix côte de boeuf" not "beef price"
- Modalities are **case-sensitive codes** (e.g., "D" for daily, "F" for female)
- `get_melodi_observations` returns empty results silently if filters don't match — **always verify modalities first**
- Some datasets have years as columns, others as modalities — check the schema

**Example**:
```
User: "How many deaths were recorded in France in 2023?"
Step 1: search_melodi_datasets(query="décès mortalité France")
  → Result: dataset_id="DS_DECES_MORTALITE", columns=["ANNEE", "GEO", "NB_DECES"]
Step 2: search_melodi_modalities(dataset_id="DS_DECES_MORTALITE", columns=["ANNEE", "GEO"], query="2023 France")
  → Result: ANNEE code="2023", GEO code="2023-FRANCE-FM"
Step 3: get_melodi_observations(dataset_id="DS_DECES_MORTALITE", filters={"ANNEE": "2023", "GEO": "2023-FRANCE-FM"})
```

---

### 3. RMES Tools (Semantic Graph / SPARQL)

**When to use**: You need concept definitions, classification hierarchies (NAF codes, PCS categories), or metadata about statistical operations.

**Tools**:
- `RMES_list_graphs` — Discover available graphs by category
- `RMES_describe_resource` — Get all properties of a specific RDF resource
- `RMES_run_sparql` — Execute custom SPARQL queries

**Workflow**:
```
1. RMES_list_graphs → Find the relevant graph category
2. RMES_describe_resource → Explore a specific concept (if you know its URI)
3. RMES_run_sparql → Query the graph with SPARQL
```

**Graph categories** (from `RMES_list_graphs`):
- `nomenclatures` — Official classifications (NAF, PCS, COICOP, etc.)
- `concepts` — Statistical definitions and themes
- `operations_statistiques` — Survey and data collection metadata
- `codes_concepts_generiques` — Cross-cutting coding concepts
- `qualite_rapports` — Quality reports per statistical operation
- `geographie` — Geographic codes (COG)
- `demographie` — Legal populations by year

**SPARQL query patterns**:

**Find NAF codes containing a keyword**:
```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?s ?label WHERE {
  GRAPH <http://rdf.insee.fr/graphes/codes/naf2025> {
    ?s skos:prefLabel ?label .
    FILTER(lang(?label) = "fr")
    FILTER(CONTAINS(LCASE(STR(?label)), "extraction"))
  }
} LIMIT 10
```

**Find concept definitions**:
```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xkos: <http://rdf-vocabulary.ddialliance.org/xkos#>
SELECT ?concept ?label ?definitionText WHERE {
  GRAPH <http://rdf.insee.fr/graphes/concepts/definitions> {
    ?concept skos:prefLabel ?label ;
             skos:definition ?definitionResource .
    ?definitionResource xkos:plainText ?definitionText .
    FILTER(lang(?label) = "fr")
    FILTER(lang(?definitionText) = "fr")
    FILTER(CONTAINS(LCASE(STR(?label)), "inflation"))
  }
} LIMIT 10
```

**Critical rules**:
- **Always use `GRAPH <uri>`** to scope queries — scanning all graphs is slow and often times out
- **Always add `FILTER(lang(?label) = "fr")`** on SKOS labels to avoid multilingual duplicates
- **Add `LIMIT`** to prevent huge responses (the tool auto-adds one if missing, but explicit is better)
- RMES does **NOT** contain observations — use MELODI for actual data points

**Example**:
```
User: "What are the NAF 2025 codes for mining activities?"
→ RMES_list_graphs(category="nomenclatures") → Confirm naf2025 exists
→ RMES_run_sparql with the NAF query pattern above
```

---

## Common Pitfalls and How to Avoid Them

### 1. Guessing identifiers
❌ **Wrong**: `get_melodi_observations(dataset_id="inflation")`  
✅ **Right**: `search_melodi_datasets(query="indice prix consommation")` → extract `dataset_id`

### 2. Skipping modality discovery
❌ **Wrong**: `get_melodi_observations(filters={"GEO": "France"})`  
✅ **Right**: `search_melodi_modalities(columns=["GEO"], query="France")` → get exact code

### 3. Using English queries
❌ **Wrong**: `search_insee_documents(query="unemployment rate")`  
✅ **Right**: `search_insee_documents(query="taux chômage France")`

### 4. SPARQL without GRAPH scope
❌ **Wrong**: `SELECT ?s WHERE { ?s ?p ?o } LIMIT 10` (scans 700+ graphs)  
✅ **Right**: `SELECT ?s WHERE { GRAPH <http://rdf.insee.fr/graphes/codes/naf2025> { ?s ?p ?o } } LIMIT 10`

### 5. Fetching documents without searching first
❌ **Wrong**: `get_insee_document(url="/fr/statistiques/12345")` (guessed URL)  
✅ **Right**: `search_insee_documents(query="...")` → extract URL from results

---

## Feedback and Error Reporting

**Tool**: `send_feedback`

**When to use**:
- A tool returns unexpected results or errors
- You discover a bug or limitation
- The user reports an issue with tool behavior
- You have suggestions for improving tool descriptions or workflows

**Format**: Write feedback as if filing a GitHub issue — include context, expected vs actual behavior, and proposed solutions.

**Example**:
```
send_feedback(
  username="assistant_session_abc",
  feedback="## Bug Report\n\n**Tool**: search_melodi_datasets\n\n**Issue**: Query 'prix pain' returns no results, but dataset DS_PRIX_PAIN exists.\n\n**Expected**: Should find at least one matching dataset.\n\n**Proposed fix**: Check if the Elasticsearch index includes this dataset."
)
```

---

## Verification Checklist

Before responding to the user, verify:

- [ ] Identified the correct data source (insee.fr, MELODI, or RMES) based on query type
- [ ] For MELODI queries: followed the 3-step workflow (search → modalities → observations)
- [ ] For insee.fr queries: used French keywords in search queries
- [ ] For RMES queries: included `GRAPH <uri>` clause in SPARQL
- [ ] For RMES queries: added `FILTER(lang(?label) = "fr")` on SKOS labels
- [ ] Never guessed dataset IDs, URLs, or modality codes — always discovered them first
- [ ] If a tool returned an error or unexpected results, used `send_feedback` to report it
