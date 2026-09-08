"""Server-level guidance, sent to every client during the MCP handshake.

Assembled from the enabled tool families, so a deployment never advertises a workflow whose tools are not registered.
"""

from textwrap import dedent

# language=Markdown
OVERVIEW = """
    ## OVERVIEW

    This server exposes INSEE (French national statistics) data through three sources:

    - insee.fr -- publications, rapid releases and headline indicators
    - MELODI -- the dataset catalogue and the observations themselves
    - RMES -- statistical metadata: definitions and nomenclatures. It holds no figures.
"""

# language=Markdown
GLOBAL_RULES = """
    ## RULES THAT APPLY TO EVERY TOOL

    - Never guess a dataset id, a modality code, a document URL or a graph URI. Each is opaque and must come from a
      discovery call first.
    - The data is French. Search with French keywords and rich synonyms.
    - An empty result is a valid answer, not a failure. It usually means the filters were too narrow.
"""

# language=Markdown
INSEE_SECTION = """
    ## insee.fr TOOLS

    ROUTING PRIORITY
    - Simple statistics (population, inflation, chomage, PIB, salaires) by region/department?
      -> Use `search_insee_chiffrecle` FIRST.
    - Granular product data (e.g., beef rib price 2000)? -> Use `search_melodi_datasets` FIRST.
    - `search_insee_documents` is for ANALYSIS, CONTEXT, and COMPLEX NARRATIVES.

    ### `search_insee_chiffrecle`

    WHEN TO USE
    - Population, inflation, chomage, PIB, salaires, prix par categorie, comparaisons geographiques (region,
      departement, commune).
    - Cas simples : 'Quelle est la population de X ?', 'Taux de chomage en 2024 ?', 'Inflation en juillet 2026 ?'

    WHEN NOT TO USE
    - Analyses detaillees, impacts/contexte, tendances complexes, donnees produit granulaires historiques
      -> `search_melodi_datasets` ou `search_insee_documents` selon le contexte.

    ### `search_insee_documents`

    WHEN TO USE
    - Impact analyses (e.g., 'covid effects on tourism').
    - Historical evolution and trends (e.g., 'unemployment 1990-2026').
    - Detailed methodological or definitional content.
    - Regional/departmental profiles with socioeconomic context.
    - Specific thematic deep-dives (demography, labour market, inequalities, environment, housing, ...).
    - Comparative studies or cross-cutting analyses.

    WHEN NOT TO USE
    - Simple factual questions ('What is X region's population?') -> `search_insee_chiffrecle`.
    - Quick, up-to-date headline indicators -> `get_insee_homepage`.
    - Latest monthly/quarterly rapid releases -> `search_insee_conjoncture`.
    - Vocabulary / code definitions / classifications -> `run_rmes_sparql`.
    - Granular historical time series (product prices, individual wages) -> `search_melodi_datasets`.

    ### `search_insee_conjoncture`

    WHEN TO USE
    - The user asks for the *latest* monthly/quarterly release of a named indicator (e.g. last month's consumer
      confidence, last quarter's GDP estimate). Prefer the most recent edition.

    WHEN NOT TO USE
    - Generic up-to-date indicator on the homepage: `get_insee_homepage`.
    - Deep, peer-reviewed analysis: `search_insee_documents`.

    ### `get_insee_homepage`

    WHEN TO USE
    - Preferred FIRST step for any generic, up-to-date statistical question. It gives the most recent official
      figure instantly, without searching individual documents.

    WHEN NOT TO USE
    - User asks for a previous year's figure. Use `search_insee_documents` or `search_insee_conjoncture` with
      `year_of_reference`.

    WORKFLOW
    1. Call this tool.
    2. Present the indicator value, quoting the period it states.
    3. Follow up with `search_insee_documents` or `search_insee_conjoncture` if the user needs deeper tables,
       historic series, or a source document.

    ### `get_insee_document`

    WHEN TO USE
    - You have a concrete URL of the form `/fr/statistiques/<id>` or `/fr/statistiques/<id>?sommaire=<sid>`,
      returned by one of the searches above.

    WHEN NOT TO USE
    - You are still looking for the right publication. Use `search_insee_documents` first.
    - You need a quick, up-to-date indicator. Use `get_insee_homepage`.
"""

# language=Markdown
MELODI_SECTION = """
    ## MELODI TOOLS

    WORKFLOW (chain these three, in order)
    1. `search_melodi_datasets` -> dataset_id + column ids
    2. `search_melodi_modalities` -> exact modality codes for filtering
    3. `get_melodi_observations` -> final observations

    ### `search_melodi_datasets`

    WHEN TO USE
    - The user asks for a specific statistic (price of a product, mortality by region, frequency of a name, etc.)
      and you need to locate the right dataset before fetching rows.

    WHEN NOT TO USE
    - Generic, up-to-date indicator questions (use `get_insee_homepage`).
    - Full-text analysis of a published report (use `search_insee_documents`).
    - Definition/ontology lookups (use `run_rmes_sparql`).

    ### `search_melodi_modalities`

    WHEN TO USE
    - You have a `dataset_id` (from `search_melodi_datasets`) and want to find the exact modality code for a
      concept like `cote de boeuf`, `Ile-de-France`, or `female Maria`.

    WHEN NOT TO USE
    - You don't yet know the dataset. Run `search_melodi_datasets` first.

    ### `get_melodi_observations`

    WHEN TO USE
    - You already know the exact `dataset_id` (from `search_melodi_datasets`) AND the modality codes you want to
      filter on (from `search_melodi_modalities`).

    WHEN NOT TO USE
    - You are still looking for the right dataset. Use `search_melodi_datasets` first.
    - You need concept definitions or code-list vocabularies. Use `run_rmes_sparql`.
"""

# language=Markdown
RMES_SECTION = """
    ## RMES TOOLS

    RMES holds metadata, definitions and nomenclatures. It holds no figures -- for actual data points use the
    MELODI workflow.

    ### `search_rmes_graphs`

    WHEN TO USE
    - FIRST, to discover which graphs exist before writing a SPARQL query with `run_rmes_sparql` -- there are more
      than 700 graphs.

    ### `describe_rmes_resource`

    WHEN TO USE
    - You already know a resource URI and want every property attached to it.

    ### `run_rmes_sparql`

    WHEN TO USE
    - Vocabulary, code definitions and classifications, once you know which graphs to target.

    WHEN NOT TO USE
    - You have not called `search_rmes_graphs` yet. Call it first to learn the available graph categories.
"""


def build_instructions(
    enable_inseefr_tools: bool,
    enable_melodi_tools: bool,
    enable_rmes_tools: bool,
) -> str:
    """Assemble the guidance for the tool families this deployment actually registers."""
    sections = [OVERVIEW, GLOBAL_RULES]
    if enable_inseefr_tools:
        sections.append(INSEE_SECTION)
    if enable_melodi_tools:
        sections.append(MELODI_SECTION)
    if enable_rmes_tools:
        sections.append(RMES_SECTION)
    return "\n\n".join(dedent(section).strip() for section in sections)
