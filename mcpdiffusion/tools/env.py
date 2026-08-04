"""
Tool metadata (name, description, version) and shared enums.

Design notes:
- Tool *names* are English snake_case; French is kept only where it is
  actual data (enum literals that hit the ES index, user-supplied queries).
- `CURRENT_DATE` is computed lazily so long-running servers always report
  today's date, not the day the process started.
- `ES_HOST` is the single source of truth for the Elasticsearch endpoint.
- Tool descriptions describe the *final* schemas; rewrite in lockstep
  when schemas change.
"""
from datetime import date
from typing import Literal


def current_date_iso() -> str:
    """Return today's date as ISO-8601. Called at description render time
    so a long-running server doesn't ship stale dates to models."""
    return date.today().isoformat()


# --- MELODI tools -----------------------------------------------------------

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
        "synonyms: e.g. `\"indice des prix a la consommation\"`, "
        "`\"deces par departement\"`, `\"prenoms des nouveau-nes\"`.\n"
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
        "- `columns_id` -- which columns to search (e.g. `[\"PRICES\", \"GEO\"]`).\n"
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
        "or more explicit URLs (e.g. from `search_insee_documents` or from "
        "the `link` fields returned by `get_insee_homepage`).\n"
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
        "`[\"/fr/statistiques/4277658?sommaire=4318291\"]`).\n"
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

SEARCH_DOCUMENTS = {
    "tool_name": "search_insee_documents",
    "tool_description": (
        "Search the INSEE catalogue of official statistical publications "
        "(Insee Premiere, Insee Analyses, Dossiers, References, Focus, ...). "
        "Returns structured publication records; pass the URL of a record to "
        "`get_insee_document` to fetch the full text.\n"
        "\n"
        "⚠️ ROUTING PRIORITY\n"
        "- Simple statistics (population, inflation, chômage, PIB, salaires) "
        "by region/department? → Use `search_chiffres_clefs_insee` FIRST.\n"
        "- Granular product data (e.g., beef rib price 2000)? → Use "
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
        "- Simple factual questions ('What is X region's population?') → "
        "`search_chiffres_clefs_insee`.\n"
        "- Quick, up-to-date headline indicators → `get_insee_homepage`.\n"
        "- Latest monthly/quarterly rapid releases → `search_insee_conjoncture`.\n"
        "- Vocabulary / code definitions / classifications → `query_insee_rmes`.\n"
        "- Granular historical time series (product prices, individual wages) → "
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
        "EXAMPLES\n"
        "✅ 'impacts du covid sur l'emploi en Île-de-France' → this tool\n"
        "✅ 'inégalités de revenus régionales' → this tool\n"
        "❌ 'population Loire-Atlantique 2025' → search_chiffres_clefs_insee\n"
        "❌ 'prix côte de boeuf 2000' → search_melodi_datasets\n"
        "\n"
        "OUTPUT\n"
        "List of publications: `{ id, score, titre, soustitre, chapo, "
        "anneediffusion, zone, theme, url }`. Feed `url` to `get_insee_document`.\n"
        f"\n"
        f"Current date is {current_date_iso()}.\n"
    ),
    "tool_metadata": {"version": "6.0", "author": "mirlon"},
}

SEARCH_CHIFFRECLEF = {
    "tool_name": "search_insee_chiffrecle",
    "tool_description": "Recherche EXCLUSIVE dans les Chiffres-clefs INSEE : données synthétiques, \n"
    "comparaisons régionales/départementales et statistiques factuelles simples.\n"
    "À utiliser EN PRIORITÉ pour : population, inflation, chômage, PIB, salaires, \n"
    "prix par catégorie, comparaisons géographiques (région, département, commune).\n"
    "À utiliser POUR LES CAS SIMPLES : 'Quelle est la population de X ?', 'Taux de chômage en 2024 ?', 'Inflation en juillet 2026 ?'\n"
    "À NE PAS utiliser pour : analyses détaillées, impacts/contexte, tendances \n"
    "complexes, données produit granulaires historiques (→ utiliser search_melodi_datasets \n"
    "ou search_insee_documents selon le contexte).\n"
    "Retourne directement les tableaux synthétiques prêts à l'emploi.\n",
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
        f"\n"
        f"Current date is {current_date_iso()}.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

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
        "- `mainIndicators` -- each with name, value, description and a link "
        "to the underlying official product (pass the link to `get_insee_document`).\n"
        "- `lastArticles` -- recent short articles with title, date, "
        "collection and link.\n"
        "- `keyGraphics` -- selection of recent graphical publications.\n"
        "\n"
        "WORKFLOW\n"
        "1. Call this tool.\n"
        "2. Present the indicator value + description + link.\n"
        "3. Follow up with `search_insee_documents` or `search_insee_conjoncture` "
        "only if the user needs deeper tables or historic series.\n"
        f"\n"
        f"Current date is {current_date_iso()}.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

# --- RMES (SPARQL) ----------------------------------------------------------

RMES_SPARQL = {
    "tool_name": "query_insee_rmes",
    "tool_description": (
        "Run a SPARQL query against the INSEE semantic graph (RMES). "
        "RMES holds INSEE metadata, concepts, definitions and code lists "
        "(SKOS / XKOS). It does NOT hold observations.\n"
        "\n"
        "WHEN TO USE\n"
        "- Concept definitions (`\"what is inflation\"`).\n"
        "- Code-list lookups (NAF 2025 activity codes, PCS 2020, CPFR 21, "
        "COICOP 2018, ...).\n"
        "\n"
        "WHEN NOT TO USE\n"
        "- Actual data points or observations (use Melodi tools).\n"
        "- Published reports (use INSEE.fr tools).\n"
        "\n"
        "INPUT\n"
        "- `sparql_query` -- a complete, valid SPARQL query. Do NOT wrap it "
        "in quotes. Generate it from one of the two templates below.\n"
        "\n"
        "GRAPH 1: code lists (`/graphes/codes/xxx`)\n"
        "Allowed `xxx`: naf2025, pcsese2017, emb2026, eap2025, cpfr21, "
        "coicop2018, pcs2020. Template (find up to 10 codes whose text "
        "contains a keyword):\n"
        "\n"
        "    SELECT ?g ?s ?p ?o\n"
        "    WHERE {\n"
        "      VALUES ?g { <http://rdf.insee.fr/graphes/codes/naf2025> }\n"
        "      GRAPH ?g {\n"
        "        ?s ?p ?o .\n"
        "        FILTER( CONTAINS(LCASE(STR(?o)), \"extraction\") )\n"
        "      }\n"
        "    }\n"
        "    LIMIT 10\n"
        "\n"
        "GRAPH 2: concept definitions (`/graphes/concepts/definitions`)\n"
        "Enriched with SKOS + XKOS. Template (find definitions whose "
        "French label contains a keyword):\n"
        "\n"
        "    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
        "    PREFIX xkos: <http://rdf-vocabulary.ddialliance.org/xkos#>\n"
        "    SELECT ?concept ?label ?definitionText\n"
        "    WHERE {\n"
        "      GRAPH <http://rdf.insee.fr/graphes/concepts/definitions> {\n"
        "        ?concept skos:prefLabel ?label ;\n"
        "                 skos:definition ?definitionResource .\n"
        "        ?definitionResource xkos:plainText ?definitionText .\n"
        "        FILTER(lang(?label) = \"fr\")\n"
        "        FILTER(lang(?definitionText) = \"fr\")\n"
        "        FILTER( CONTAINS(LCASE(STR(?label)), LCASE(\"inflation\")) )\n"
        "      }\n"
        "    }\n"
        "    LIMIT 10\n"
        "\n"
        "OUTPUT\n"
        "The raw SPARQL JSON response on success; a structured error when "
        "the query is malformed (400) or the endpoint is unavailable.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

RMES_LIST_GRAPHS = {
    "tool_name": "RMES_list_graphs",
    "tool_description": (
        "Liste les graphes nommés disponibles dans la base RDF de l'INSEE (RMES). "
        "Utilise ce tool EN PREMIER pour découvrir quels graphes existent avant "
        "d'écrire une requête SPARQL avec RMES_run_sparql -- il y a plus de 700 graphes.\n"
        "\n"
        "Par défaut (`category=ALL`), le résultat est une vue CONDENSÉE par catégorie, "
        "avec un compteur et quelques URIs d'exemple par catégorie -- pas la liste plate "
        "des 700+ graphes. Choisis une catégorie précise dans le paramètre `category` "
        "pour cibler une famille, ou utilise `contains` pour une recherche libre par "
        "sous-chaîne. Une catégorie \"autre\" recueille tout graphe ne correspondant à "
        "aucune famille connue."
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

RMES_DESCRIBE_RESOURCE = {
    "tool_name": "RMES_describe_resource",
    "tool_description": (
        "Récupère toutes les propriétés connues (prédicat -> valeur) d'une ressource RDF "
        "identifiée par son URI complète. Combine automatiquement les propriétés où la "
        "ressource est sujet ET celles où elle est objet (utile pour remonter des relations "
        "skos:broader par exemple). Restreins avec `graph` si tu sais déjà où chercher -- "
        "sinon la recherche se fait sur tous les graphes, ce qui est plus lent."
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}

RMES_RUN_SPARQL = {
    "tool_name": "RMES_run_sparql",
    "tool_description": (
        "Exécute une requête SPARQL libre sur RMES, la base de métadonnées, nomenclatures "
        "et définitions de l'INSEE (elle ne contient PAS les chiffres/données, voir "
        "get_MELODI_datasets pour ça).\n"
        "\n"
        "AVANT d'écrire une requête complexe : appelle RMES_list_graphs pour connaître les "
        "catégories de graphes disponibles.\n"
        "\n"
        "Bonnes pratiques :\n"
        "- Toujours filtrer sur un ou plusieurs graphes précis avec GRAPH <uri> { ... } ou "
        "  VALUES ?g { <uri1> <uri2> } plutôt que de scanner tous les graphes.\n"
        "- Toujours ajouter FILTER(lang(?label) = \"fr\") sur les littéraux SKOS pour éviter "
        "  les doublons multilingues.\n"
        "- Une clause LIMIT est fortement recommandée ; si absente, `max_rows` est ajoutée "
        "  automatiquement (indiqué dans la réponse via `limit_added`/`hint`).\n"
        "- Vocabulaires : skos (concepts, labels, broader/narrower), xkos (nomenclatures "
        "  statistiques : ClassificationLevel, ExplanatoryNote), dcterms (métadonnées), "
        "  rdf.insee.fr/def/{geo,demo,base}# (vocabulaires INSEE).\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}


# --- Shared enums / constants ----------------------------------------------

INSEE_GEO = Literal[
    "COM",
    "DEP",
    "REG",
    "INTER",
    "COMPRD",
    "FRANCE",
]


INSEE_THEME_NIV1 = Literal[
    "Demographie",
    "Revenus - Pouvoir d'achat - Consommation",
    "Conditions de vie - Societe",
    "Marche du travail - Salaires",
    "Economie - Conjoncture - Comptes nationaux",
    "Developpement durable - Environnement",
    "Entreprises",
    "Secteurs d'activite",
    "Territoires, villes et quartiers",
]


KEYS_THEME_NIV1 = {
    "Demographie": 0,
    "Conditions de vie - Societe": 6,
    "Marche du travail - Salaires": 20,
    "Economie - Conjoncture - Comptes nationaux": 27,
    "Entreprises": 37,
    "Secteurs d'activite": 44,
    "Territoires, villes et quartiers": 68,
    "Developpement durable - Environnement": 74,
    "Revenus - Pouvoir d'achat - Consommation": 80,
    "Methodes": 86,
}


DICT_GEO = {
    "COMMUNE": "COM",
    "DEPARTEMENT": "DEP",
    "REGION": "REG",
    "INTERNATIONAL": "INTER",
    "INTER REGION": "COMPRD",
    "FRANCE": "FRANCE",
}


DICT_THEME_CONJ = {
    "Industrial production and activity": [
        "Indice de la production industrielle ",
        "Enquete mensuelle de conjoncture dans l'industrie",
        "Enquete trimestrielle de conjoncture dans l'industrie",
        "Chiffre d'affaires dans l'industrie et la construction",
        "Indices des commandes en valeur recues dans l'industrie",
        "Enquete sur les investissements dans l'industrie",
        "Enquete de tresorerie dans l'industrie",
    ],
    "Construction and building sector": [
        "Enquete mensuelle de conjoncture dans l'industrie du batiment",
        "Enquete trimestrielle dans les travaux publics",
        "Enquete trimestrielle dans l'artisanat du batiment",
        "Construction de locaux",
        "Index batiment, travaux publics et divers de la construction",
        "Indices des couts de production dans la construction",
        "Indice des prix d'entretien-amelioration des batiments",
        "Indice du cout de la construction",
    ],
    "Housing and real estate": [
        "Enquete trimestrielle dans la promotion immobiliere",
        "Indice de reference des loyers",
        "Indice des loyers commerciaux",
        "Indice des loyers des activites tertiaires",
        "Indices des loyers d'habitation",
        "Indice des prix des logements neufs et anciens",
        "Indices des prix des logements anciens",
        "Commercialisation de logements neufs - Ventes aux particuliers et ventes aux institutionnels",
    ],
    "Retail, wholesale and services": [
        "Enquete mensuelle de conjoncture dans le commerce de detail et le commerce et la reparation automobiles",
        "Enquete mensuelle de conjoncture dans les services",
        "Enquete bimestrielle de conjoncture dans le commerce de gros",
        "Volume des ventes dans le commerce de detail et les services personnels ",
        "Volume des ventes dans le commerce",
        "Chiffre d'affaires dans le commerce de gros et divers services aux entreprises",
        "Indice de production dans les services",
        "Chiffre d'affaires des grandes surfaces alimentaires (parution arretee aux resultats de decembre 2022)",
    ],
    "Business demographics and confidence": [
        "Creations d'entreprises",
        "Defaillances d'entreprises (parution arretee aux resultats de juillet 2012)",
        "Climat des affaires",
        "Notes et Points de conjoncture nationaux",
        "Conjoncture regionale",
    ],
    "Employment, unemployment and labour market": [
        "Estimation flash de l'emploi salarie",
        "Emploi salarie",
        "Emploi et taux de chomage localises (par region et departement)",
        "Emploi salarie, salaires de base et duree du travail (resultats definitifs)",
        "Emploi salarie, salaires de base et duree du travail (resultats provisoires)",
        "Chomage au sens du BIT et indicateurs sur le marche du travail (resultats de l'enquete Emploi)",
        "Les inscrits a France Travail",
    ],
    "Wages and labour costs": [
        "Indice du cout horaire du travail revise - Tous salaries (ICHT, ICHTrev-TS) - Publication arretee depuis le 06/10/2023",
        "Indice du cout du travail (ICT) - Resultats detailles",
        "Indice du cout du travail (ICT) - Estimation flash",
        "Salaires de base - Comparaison France-Allemagne",
    ],
    "Public sector employment and pay": [
        "L'emploi dans la fonction publique",
        "Indice de traitement brut dans la fonction publique d'Etat - grille indiciaire",
        "Les salaires dans la fonction publique",
    ],
    "Households, consumption and health": [
        "Consommation de soins et biens medicaux (CSBM)",
        "Prestations et ressources de protection sociale",
        "Depenses de consommation des menages en biens",
        "Enquete mensuelle de conjoncture aupres des menages ",
    ],
    "Inflation and producer prices": [
        "Prix a la consommation - moyennes annuelles",
        "Indice des prix a la consommation - resultats definitifs",
        "Indice des prix a la consommation - resultats provisoires",
        "Indices de prix de production et d'importation de l'industrie",
        "Indices des prix de production des services ",
        "Indices des prix agricoles",
        "Prix des energies et des matieres premieres importees",
        "Indice des prix dans la grande distribution (parution arretee aux resultats de decembre 2025)",
    ],
    "National accounts and public finance": [
        "Comptes nationaux trimestriels - premiere estimation",
        "Comptes nationaux trimestriels - deuxieme estimation",
        "Comptes nationaux trimestriels - resultats detailles",
        "Comptes nationaux annuels - revision des principaux agregats",
        "Comptes nationaux des administrations publiques - premiers resultats",
        "Situation mensuelle budgetaire de l'Etat",
        "Dette trimestrielle de Maastricht des administrations publiques",
        "Recettes fiscales de l'Etat",
    ],
    "Transport and tourism": [
        "Immatriculations de vehicules neufs",
        "Frequentation touristique dans les hotels, campings et autres hebergements collectifs touristiques",
    ],
    "Business financing": [
        "Enquete annuelle credit-bail",
    ],
}


THEME_CONJ = Literal[
    "Industrial production and activity",
    "Construction and building sector",
    "Housing and real estate",
    "Retail, wholesale and services",
    "Business demographics and confidence",
    "Employment, unemployment and labour market",
    "Wages and labour costs",
    "Public sector employment and pay",
    "Households, consumption and health",
    "Inflation and producer prices",
    "National accounts and public finance",
    "Transport and tourism",
    "Business financing",
]

# --- Extras -----------------------------------------------------------------

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
        "\n"
        "EXAMPLES\n"
        "✅ User: 'The search_melodi_datasets tool returned no results for \"prix du pain\" even though "
        "the dataset exists.' → Log this as a bug report.\n"
        "✅ User: 'It would be helpful if RMES_list_graphs could filter by triple count range.' → "
        "Log this as a feature request.\n"
        "✅ Assistant: 'During execution of get_insee_document, the markdown parser failed on nested "
        "tables. This should be fixed.' → Log this as a technical issue.\n"
    ),
    "tool_metadata": {"version": "5.0", "author": "mirlon"},
}
