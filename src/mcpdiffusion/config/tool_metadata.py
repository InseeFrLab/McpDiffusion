"""Tool metadata (name, description, version).

Design notes:
- Tool *names* are English snake_case; French is kept only where it is
  actual data (enum literals that hit the ES index, user-supplied queries).
  Fixme: the current is computed only once at import time,
    if the server is running for 3 weeks, the old date will still be in effect...
- `CURRENT_DATE` is computed lazily so long-running servers always report
  today's date, not the day the process started.
- Tool descriptions describe the *final* schemas; rewrite in lockstep
  when schemas change.
"""

from datetime import date


# Fixme: I'd put such a generic function in a separate module
#   just a preference, not mandatory
def compute_current_date_iso() -> str:
    """Return today's date as ISO-8601."""
    return date.today().isoformat()


# Fixme: I feel like having the tools metadata separate / not-colocated with the tools might be a mistake
# Fixme: I believe those metadata can live with the corresponding set of tool functions
#  by leveraging FastMCP capabilities - descriptions could live in the functions' docstring
# Fixme: I would also create one file per tool as a preference, but I get the argument
#  of having a clear overview of tools at the same place
# --- MELODI tools -----------------------------------------------------------

# Fixme: if keeping those metadata separate, prefer multiline strings that read better
#   and avoid missing spaces issues
GET_DATASET = {
    "tool_name": "get_melodi_observations",
    "tool_description": (
        "Retrieve a filtered set of observations from a Melodi dataset. "
        "The Melodi API holds official, high-granularity statistics "
        "(prices, mortality, names, etc.).\n"
        "\n"
        "WHEN TO USE\n"
        "- You already know the exact `dataset_id` (from `search_melodi_datasets`) "
        "AND the modality codes you want to filter on "
        "(from `search_melodi_modalities`).\n"
        "\n"
        "WHEN NOT TO USE\n"
        "- You are still looking for the right dataset. Use `search_melodi_datasets` first.\n"
        "- You need concept definitions or code-list vocabularies. Use `query_insee_rmes`.\n"
        "\n"
        "WORKFLOW (chain with companion tools)\n"
        "1. `search_melodi_datasets` -> dataset_id + column ids\n"
        "2. `search_melodi_modalities` -> exact modality codes for filtering\n"
        "3. THIS TOOL (`get_melodi_observations`) -> final observations\n"
        "\n"
        "OUTPUT\n"
        "A list of observations with dimensions, attributes and the numeric "
        "measure (with unit). Returns an empty list when no rows match; "
        "a structured error when the upstream API fails or inputs are invalid.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

SEARCH_DATASET = {
    "tool_name": "search_melodi_datasets",
    "tool_description": (
        "Search the INSEE Melodi dataset catalogue by French-language natural "
        "language query. Each dataset has a unique `dataset_id`; the tool maps "
        "the query to internal metadata to return the most relevant matches.\n"
        "\n"
        "WHEN TO USE\n"
        "- The user asks for a specific statistic (price of a product, "
        "mortality by region, frequency of a name, etc.) and you need to "
        "locate the right dataset before fetching rows.\n"
        "\n"
        "WHEN NOT TO USE\n"
        "- Generic, up-to-date indicator questions (use `get_insee_homepage`).\n"
        "- Full-text analysis of a published report (use `search_insee_documents`).\n"
        "- Definition/ontology lookups (use `query_insee_rmes`).\n"
        "\n"
        "TIPS\n"
        "- Matching is lexical. Make `french_query` explicit and rich in French "
        'synonyms: e.g. `"indice des prix a la consommation"`, '
        '`"deces par departement"`, `"prenoms des nouveau-nes"`.\n'
        "- Use `start_year` / `end_year` to narrow the temporal range. Leaving "
        "both at default covers all years.\n"
        "\n"
        "NEXT STEP\n"
        "Pass the returned `dataset_id` and column ids to "
        "`search_melodi_modalities`, then feed the resolved codes into "
        "`get_melodi_observations`.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

SEARCH_MODALITIES = {
    "tool_name": "search_melodi_modalities",
    "tool_description": (
        "Given a Melodi dataset and one or more column identifiers, rank the "
        "most relevant modalities (codes/labels) for a free-text French query. "
        "The result is what you need to filter rows in `get_melodi_observations`.\n"
        "\n"
        "WHEN TO USE\n"
        "- You have a `dataset_id` (from `search_melodi_datasets`) and want "
        "to find the exact modality code for a concept like `cote de boeuf`, "
        "`Ile-de-France`, or `female Maria`.\n"
        "\n"
        "WHEN NOT TO USE\n"
        "- You don't yet know the dataset. Run `search_melodi_datasets` first.\n"
        "\n"
        "INPUT\n"
        "- `dataset_id` -- from a previous search result.\n"
        '- `columns_id` -- which columns to search (e.g. `["PRICES", "GEO"]`).\n'
        "- `french_query` -- natural-language query in French.\n"
        "\n"
        "OUTPUT\n"
        "A list of matching columns, each containing its `code`, metadata text "
        "and the top-scoring `matching_modalities` with `code`, `label_fr`, "
        "`label_en` and `score`. Empty list when nothing matches.\n"
        "\n"
        "NEXT STEP\n"
        "Use the modality `code` values as entries in "
        "`get_melodi_observations.dict_of_columns_and_values`.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

# --- INSEE.fr tools ---------------------------------------------------------

GET_DOCUMENT = {
    "tool_name": "get_insee_document",
    "tool_description": (
        "Fetch and parse a single INSEE publication from a known URL and "
        "return its full text in markdown. Use ONLY when you already have one "
        "or more explicit URLs, from `search_insee_documents`, "
        "`search_insee_conjoncture` or `search_insee_chiffrecle`.\n"
        "\n"
        "WHEN TO USE\n"
        "- You have a concrete URL of the form `/fr/statistiques/<id>` or "
        "`/fr/statistiques/<id>?sommaire=<sid>`.\n"
        "\n"
        "WHEN NOT TO USE\n"
        "- You are still looking for the right publication. Use "
        "`search_insee_documents` first.\n"
        "- You need a quick, up-to-date indicator. Use `get_insee_homepage`.\n"
        "\n"
        "INPUT\n"
        "- `list_of_url` -- list of relative URLs to fetch (e.g. "
        '`["/fr/statistiques/4277658?sommaire=4318291"]`).\n'
        "- `include_sommaire` -- also parse the page's table-of-contents "
        "section. Use once to discover the structure of a multi-section "
        "publication, then turn it off for subsequent requests on the same page.\n"
        "- `truncate_content` -- when True (default), long markdown bodies are "
        "clipped to keep the response compact for the model; set to False only "
        "when you genuinely need the full text.\n"
        "\n"
        "OUTPUT\n"
        "A uniform envelope: `{ status, results: [ { id, status, "
        "markdown_content, sommaire, error, truncated } ], count }`. Each "
        "per-URL entry has the same keys whether it succeeded or failed, so "
        "downstream code can iterate without type-sniffing.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

# Fixme: Those docstrings are computed once at import time, therefore, the current date is never re-computed
SEARCH_DOCUMENTS = {
    "tool_name": "search_insee_documents",
    "tool_description": (
        "Search the INSEE catalogue of official statistical publications "
        "(Insee Premiere, Insee Analyses, Dossiers, References, Focus, ...). "
        "Returns structured publication records; pass the URL of a record to "
        "`get_insee_document` to fetch the full text.\n"
        "\n"
        "ROUTING PRIORITY\n"
        "- Simple statistics (population, inflation, chomage, PIB, salaires) "
        "by region/department? -> Use `search_chiffres_clefs_insee` FIRST.\n"
        "- Granular product data (e.g., beef rib price 2000)? -> Use "
        "`search_melodi_datasets` FIRST.\n"
        "- This tool is for ANALYSIS, CONTEXT, and COMPLEX NARRATIVES.\n"
        "\n"
        "WHEN TO USE THIS TOOL\n"
        "- Impact analyses (e.g., 'covid effects on tourism').\n"
        "- Historical evolution and trends (e.g., 'unemployment 1990-2026').\n"
        "- Detailed methodological or definitional content.\n"
        "- Regional/departmental profiles with socioeconomic context.\n"
        "- Specific thematic deep-dives (demography, labour market, inequalities, "
        "environment, housing, ...). \n"
        "- Comparative studies or cross-cutting analyses.\n"
        "\n"
        "WHEN NOT TO USE THIS TOOL\n"
        "- Simple factual questions ('What is X region's population?') -> "
        "`search_chiffres_clefs_insee`.\n"
        "- Quick, up-to-date headline indicators -> `get_insee_homepage`.\n"
        "- Latest monthly/quarterly rapid releases -> `search_insee_conjoncture`.\n"
        "- Vocabulary / code definitions / classifications -> `query_insee_rmes`.\n"
        "- Granular historical time series (product prices, individual wages) -> "
        "`search_melodi_datasets`.\n"
        "\n"
        "HOW TO SEARCH WELL\n"
        "- `query` -- rich natural-language query with synonyms, context, "
        "and target year/geography if relevant.\n"
        "- `chiffre_clef=False` (default) -- general publications. Set to True "
        "ONLY for 'essentials sur...' publications (essentiel sur l'inflation, "
        "etc.), but prefer `search_chiffres_clefs_insee` for those instead.\n"
        "- `geo_niveau` + `geo_keyword` -- territorial filtering "
        "(COM/DEP/REG/INTER/COMPRD/FRANCE).\n"
        "- `theme` -- restrict to top-level theme (Demographie, "
        "Marche du travail, Economie, etc.). Default ALL.\n"
        "- `year_of_reference` -- hard filter on publication year; null = all years.\n"
        "\n"
        "OUTPUT\n"
        "List of publications: `{ id, score, titre, soustitre, chapo, "
        "anneediffusion, zone, theme, url }`. Feed `url` to `get_insee_document`.\n"
        "\n"
        f"Current date is {compute_current_date_iso()}.\n"
    ),
    "tool_metadata": {"version": "6.0", "author": "mirlon"},
}

SEARCH_CHIFFRECLEF = {
    "tool_name": "search_insee_chiffrecle",
    "tool_description": "Recherche EXCLUSIVE dans les Chiffres-clefs INSEE : donnees synthetiques, \n"
    "comparaisons regionales/departementales et statistiques factuelles simples.\n"
    "A utiliser EN PRIORITE pour : population, inflation, chomage, PIB, salaires, \n"
    "prix par categorie, comparaisons geographiques (region, departement, commune).\n"
    "A utiliser POUR LES CAS SIMPLES : 'Quelle est la population de X ?', "
    "'Taux de chomage en 2024 ?', 'Inflation en juillet 2026 ?'\n"
    "A NE PAS utiliser pour : analyses detaillees, impacts/contexte, tendances \n"
    "complexes, donnees produit granulaires historiques (-> utiliser search_melodi_datasets \n"
    "ou search_insee_documents selon le contexte).\n"
    "Retourne directement les tableaux synthetiques prets a l'emploi.\n",
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

SEARCH_CONJONCTURE = {
    "tool_name": "search_insee_conjoncture",
    "tool_description": (
        "Search INSEE Rapid Releases (Informations rapides): short, recurring "
        "publications reporting the latest monthly/quarterly/annual results for "
        "major economic and social indicators (prices, employment, production, "
        "housing, wages, national accounts, ...).\n"
        "\n"
        "WHEN TO USE\n"
        "- The user asks for the *latest* monthly/quarterly release of a "
        "named indicator (e.g. last month's consumer confidence, "
        "last quarter's GDP estimate). Prefer the most recent edition.\n"
        "\n"
        "WHEN NOT TO USE\n"
        "- Generic up-to-date indicator on the homepage: `get_insee_homepage`.\n"
        "- Deep, peer-reviewed analysis: `search_insee_documents`.\n"
        "\n"
        "HOW TO SEARCH WELL\n"
        "- `query` -- provide several synonyms and related notions; the "
        "search is lexical and rewards keyword breadth.\n"
        "- `theme_conjoncture` -- optional broad category (Industrial "
        "production and activity, Inflation and producer prices, "
        "Employment, unemployment and labour market, ...). Leave null to "
        "search across all categories.\n"
        "- `year_of_reference` -- hard filter on publication year; leave null "
        "to search all years.\n"
        "\n"
        "OUTPUT\n"
        "A list of publications: `{ id, score, titre, soustitre, chapo, "
        "anneediffusion, zone, theme, url }`.\n"
        "\n"
        f"Current date is {compute_current_date_iso()}.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

# Business rule: this description calls the figures "latest" and makes the tool the preferred FIRST step,
# but they are frozen literals (see data/indicators.py). Whether the wording softens or the data becomes
# live is the same decision. Left as-is deliberately.
GET_HOMEPAGE = {
    "tool_name": "get_insee_homepage",
    "tool_description": (
        "Retrieve the INSEE home page with the latest key indicators at national level"
        "published by the institute (population, inflation, unemployment, "
        "GDP growth, ...).\n"
        "\n"
        "WHEN TO USE -- preferred FIRST step for any generic, up-to-date "
        "statistical question. It gives the most recent official figure "
        "instantly, without searching individual documents.\n"
        "\n"
        "WHEN NOT TO USE\n"
        "- User asks for a previous year's figure. Use `search_insee_documents` "
        "or `search_insee_conjoncture` with `year_of_reference`.\n"
        "\n"
        "OUTPUT\n"
        "- `indicators` -- each with `key` (indicator name), `alias` (alternative name, often empty) "
        "and `value`, a full sentence in French stating the figure and the period it covers.\n"
        "- `count` -- number of indicators returned.\n"
        "\n"
        "WORKFLOW\n"
        "1. Call this tool.\n"
        "2. Present the indicator value, quoting the period it states.\n"
        "3. Follow up with `search_insee_documents` or `search_insee_conjoncture` "
        "if the user needs deeper tables, historic series, or a source document.\n"
        "\n"
        f"Current date is {compute_current_date_iso()}.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

# --- RMES (SPARQL) ----------------------------------------------------------

RMES_LIST_GRAPHS = {
    "tool_name": "RMES_list_graphs",
    "tool_description": (
        "Liste les graphes nommes disponibles dans la base RDF de l'INSEE (RMES). "
        "Utilise ce tool EN PREMIER pour decouvrir quels graphes existent avant "
        "d'ecrire une requete SPARQL avec RMES_run_sparql -- il y a plus de 700 graphes.\n"
        "\n"
        "Par defaut (`category=ALL`), le resultat est une vue CONDENSEE par categorie, "
        "avec un compteur et quelques URIs d'exemple par categorie -- pas la liste plate "
        "des 700+ graphes. Choisis une categorie precise dans le parametre `category` "
        "pour cibler une famille, ou utilise `contains` pour une recherche libre par "
        'sous-chaine. Une categorie "autre" recueille tout graphe ne correspondant a '
        "aucune famille connue."
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

RMES_DESCRIBE_RESOURCE = {
    "tool_name": "RMES_describe_resource",
    "tool_description": (
        "Recupere toutes les proprietes connues (predicat -> valeur) d'une ressource RDF "
        "identifiee par son URI complete. Combine automatiquement les proprietes ou la "
        "ressource est sujet ET celles ou elle est objet (utile pour remonter des relations "
        "skos:broader par exemple). Restreins avec `graph` si tu sais deja ou chercher -- "
        "sinon la recherche se fait sur tous les graphes, ce qui est plus lent."
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

RMES_RUN_SPARQL = {
    "tool_name": "RMES_run_sparql",
    "tool_description": (
        "Execute une requete SPARQL libre sur RMES, la base de metadonnees, nomenclatures "
        "et definitions de l'INSEE (elle ne contient PAS les chiffres/donnees, voir "
        "get_MELODI_datasets pour ca).\n"
        "\n"
        "AVANT d'ecrire une requete complexe : appelle RMES_list_graphs pour connaitre les "
        "categories de graphes disponibles.\n"
        "\n"
        "Bonnes pratiques :\n"
        "- Toujours filtrer sur un ou plusieurs graphes precis avec GRAPH <uri> { ... } ou "
        "  VALUES ?g { <uri1> <uri2> } plutot que de scanner tous les graphes.\n"
        '- Toujours ajouter FILTER(lang(?label) = "fr") sur les litteraux SKOS pour eviter '
        "  les doublons multilingues.\n"
        "- Une clause LIMIT est fortement recommandee ; si absente, `max_rows` est ajoutee "
        "  automatiquement (indique dans la reponse via `limit_added`/`hint`).\n"
        "- Vocabulaires : skos (concepts, labels, broader/narrower), xkos (nomenclatures "
        "  statistiques : ClassificationLevel, ExplanatoryNote), dcterms (metadonnees), "
        "  rdf.insee.fr/def/{geo,demo,base}# (vocabulaires INSEE).\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

SEND_FEEDBACK = {
    "tool_name": "send_feedback",
    "tool_description": (
        "Submit structured feedback about the MCP tools, server behavior, or user experience. "
        "This tool appends a timestamped Markdown entry to the feedback log for administrator review.\n"
        "\n"
        "WHEN TO USE\n"
        "- The user reports a bug, error, or unexpected behavior in any tool.\n"
        "- The user suggests an improvement, new feature, or enhancement.\n"
        "- The assistant encounters an issue during tool execution that should be logged.\n"
        "- After completing a complex workflow where feedback on tool quality would be valuable.\n"
        "\n"
        "WHEN NOT TO USE\n"
        "- For transient debugging or one-off troubleshooting (use terminal/logs instead).\n"
        "- For questions about tool usage (ask the user or consult documentation).\n"
        "\n"
        "INPUT\n"
        "- `username` -- identifier for the feedback author (e.g., user name, role, or session ID).\n"
        "- `feedback` -- clear, actionable Markdown describing the issue or suggestion. "
        "Include context (which tool, what happened), expected vs actual behavior, and "
        "proposed solutions if applicable. Write as if filing a GitHub issue.\n"
        "\n"
        "OUTPUT\n"
        "Confirmation message with the timestamp and path where feedback was recorded.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}
