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


# --- Dict homepage -----------------------------------------------------------------

DICT_KV = [
    {"cle": "clé", "alias": "alias", "valeur": "valeur"},
    {"cle": "estimation de population France", "alias": "", "valeur": "Au 1er janvier 2026, la population résidant en France est estimée à 69,1 millions d'habitants."},
    {"cle": "population légale France", "alias": "", "valeur": "Au 1er janvier 2023, la population de la France hors Mayotte s'établit officiellement à 68 094 000 habitants."},
    {"cle": "immigrés France", "alias": "", "valeur": "En 2025, 8,0 millions d'immigrés vivent en France, soit 11,6 % de la population totale."},
    {"cle": "population étrangère France", "alias": "", "valeur": "En 2025, la population étrangère vivant en France s'élève à 6,3 millions de personnes, soit 9,1 % de la population totale."},
    {"cle": "naissances France", "alias": "", "valeur": "En 2025, le nombre de naissances en France est estimé à 645 000, soit une baisse de -2,1 % par rapport à 2024."},
    {"cle": "indicateur conjoncturel de fécondité", "alias": "", "valeur": "En 2025, l'indicateur conjoncturel de fécondité (ICF) continue de diminuer. Il s'établit à 1,56 enfant par femme (1,53 en France métropolitaine), après 1,61 en 2024 (1,58 en France métropolitaine)."},
    {"cle": "décès France", "alias": "", "valeur": "En 2025, le nombre de décès en France est estimé à 651 000, en hausse de 1,5 % par rapport à 2024, après +0,3 % entre 2023 et 2024 (en tenant compte du fait que 2024 est une année bissextile)."},
    {"cle": "espérance de vie France", "alias": "", "valeur": "En 2025, l'espérance de vie à la naissance s'élève à 85,9 ans pour les femmes et à 80,3 ans pour les hommes. Elle augmente en 2025, de +0,1 an pour les femmes comme pour les hommes, pour atteindre un niveau historiquement élevé."},
    {"cle": "mariages France", "alias": "", "valeur": "En 2025, le nombre de mariages célébrés en France est estimé à 251 000, dont 244 000 entre personnes de sexe différent et 7 000 entre personnes de même sexe. Le nombre de mariages augmente de 1,4 % par rapport à 2024, après +2,7 % entre 2023 et 2024 (en tenant compte du fait que 2024 est une année bissextile), alors que la tendance était plutôt à la baisse avant la crise sanitaire."},
    {"cle": "ménages France", "alias": "", "valeur": "En 2023, la France hors Mayotte compte 31,3 millions de ménages."},
    {"cle": "divorces France", "alias": "", "valeur": "128 043 divorces en 2016. Note : jusqu'en 2016, les divorces étaient des décisions de justice prononcées par un juge ; depuis 2017, les divorces par consentement mutuel passent par un acte notarié et ne sont plus comptabilisés de la même façon."},
    {"cle": "inflation", "alias": "Indice des prix à la consommation – IPC ", "valeur": "En juin 2026, les prix à la consommation (IPC) augmentent de 1,8 % sur un an. Sur un mois, l’indice des prix à la consommation diminue de 0,3 %."},
    {"cle": "Chômage BIT ", "alias": "", "valeur": "Au premier trimestre 2026, le taux de chômage  en France (hors Mayotte) augmente de 0,2 point et atteint 8,1 % . Le nombre de chômeurs est de  2,6 millions de personnes."},
    {"cle": "emploi BIT", "alias": "", "valeur": "En moyenne sur l'année 2025, parmi les personnes âgées de 15 à 64 ans vivant en France, 69,3 % sont en emploi au sens du Bureau international du travail (BIT)."},
    {"cle": "PIB trimestriel", "alias": "croissance trimestrielle", "valeur": "Au premier trimestre 2026, le produit intérieur brut (PIB) en volume se replie légèrement (-0,1 %)."},
    {"cle": "PIB annuel", "alias": "croissance annuelle", "valeur": "En 2025, le PIB croît de 0,8 % en volume aux prix de l'année précédente."},
    {"cle": "Dépenses de consommation des ménages en biens", "alias": "", "valeur": "En mai 2026, les dépenses de consommation des ménages en biens rebondissent sur un mois (+0,5 % en volume après -0,5 % en avril). Les volumes sont mesurés aux prix de l'année précédente chaînés (en milliards d'euros 2020) et corrigés des variations saisonnières et des effets des jours ouvrables (CVS-CJO)."},
    {"cle": "Climat des affaires", "alias": "", "valeur": "En juin 2026, l'indicateur synthétique du climat des affaires, calculé à partir des réponses des chefs d'entreprise des principaux secteurs d'activité marchands rebondit très légèrement, à 94, en deçà de son niveau moyen."},
    {"cle": "climat de l'emploi", "alias": "", "valeur": "En juin 2026, l'indicateur du climat de l'emploi perd de nouveau trois points (après arrondi) et s'établit à 89, son niveau le plus bas depuis juin 2013 (hors crise sanitaire)."},
    {"cle": "production manufacturière", "alias": "Indice de la production industrielle - IPI", "valeur": "En mai 2026, après deux mois de hausse, la production se replie nettement dans l'industrie manufacturière (-1,0 % après +0,6 % en avril 2026). Dans l'ensemble de l'industrie, elle se replie aussi mais plus légèrement (-0,1 % après +0,3 %)."},
    {"cle": "niveau de vie", "alias": "", "valeur": "En 2024, en France métropolitaine, le niveau de vie médian de la population s'élève à 26 740 euros annuels. Il correspond à un revenu disponible de 2 228 euros par mois pour une personne seule."},
    {"cle": "pouvoir d’achat", "alias": "", "valeur": "En 2025, le pouvoir d’achat du revenu disponible (RDB) des ménages se replie de 0,4 % après une hausse de 2,7 % en 2024. Ramené au niveau individuel et en tenant compte de l’évolution de la taille des ménages, le pouvoir d’achat baisse de 0,7 % après une hausse de 2,2 % en 2024"},
    {"cle": "balance commerciale", "alias": "", "valeur": "En 2025, les exportations en volume restent soutenues (+2,3 % après +3,2 % en 2024), tandis que les importations se redressent nettement (+2,8 % après -0,6 %). De ce fait, les échanges extérieurs pèsent sur la croissance de l’activité en 2025, à hauteur de -0,2 point de PIB, après l’avoir fortement soutenue en 2023 et 2024. "},
    {"cle": "pauvreté monétaire", "alias": "", "valeur": "En 2024, 9,8 millions de personnes vivent avec un niveau de vie inférieur au seuil de pauvreté monétaire, soit 15,4 % de la population vivant dans un logement ordinaire en France métropolitaine."},
    {"cle": "patrimoine", "alias": "", "valeur": "Début 2024, la moitié des ménages vivant en France déclarent un patrimoine brut supérieur à 205 100 euros. La moitié la mieux dotée en patrimoine brut possède collectivement 93 % de la masse totale de patrimoine. "},
    {"cle": "état santé", "alias": "", "valeur": "En 2024, deux tiers des personnes âgées de 16 ans ou plus se déclarent en bonne ou très bonne santé. À l'opposé, près de 10 % jugent leur état de santé mauvais voire très mauvais."},
    {"cle": "prestation handicap", "alias": "", "valeur": "Selon leur âge et leur situation, les personnes en situation de handicap ou de perte d'autonomie peuvent prétendre à différentes prestations. Fin 2023, 44 000 personnes ont un droit ouvert à l'allocation compensatrice pour tierce personne (ACTP) et 407 000 à la prestation de compensation du handicap (PCH). Par ailleurs, 1,4 million de personnes de 60 ans ou plus ont perçu l'allocation personnalisée d'autonomie (APA) au titre du mois de décembre 2023."},
    {"cle": "dépenses liées à la culture", "alias": "", "valeur": "En 2025, les dépenses liées à la culture, au sport et aux loisirs s'élèvent à 108 milliards d'euros. Les services récréatifs, sportifs et culturels rassemblent 45 % de ces dépenses."},
    {"cle": "Parc de logements", "alias": "", "valeur": "Au 1er janvier 2025, la France hors Mayotte compte 38,4 millions de logements. 82,5 % des logements sont des résidences principales et 54,4 % des logements individuels (maisons)."},
    {"cle": "logements vacants", "alias": "", "valeur": "Après avoir fortement augmenté entre 2005 et 2019, la part des logements vacants diminue, passant de 8,1 % en 2019 à 7,7 % en 2025 ; en 2025, 3,0 millions de logements sont vacants."},
    {"cle": "résidences secondaires ou logements occasionnels", "alias": "", "valeur": "Au 1er janvier 2025, 3,8 millions de logements sont des résidences secondaires ou des logements occasionnels ; après avoir augmenté entre 2011 et 2017, leur part dans l'ensemble du parc est stable."},
    {"cle": "ménages sont propriétaires de leur résidence principale", "alias": "", "valeur": "Au 1er janvier 2025, 57,4 % des ménages sont propriétaires de leur résidence principale."},
    {"cle": "smic", "alias": "Salaire minimum interprofessionnel de croissance", "valeur": "Depuis le 1er janvier 2026, le Smic brut s'élève à 12,02 euros par heure, soit 1 823,03 euros par mois pour 151,67 heures de travail."},
    {"cle": "salaire mensuel moyen en équivalent temps plein (EQTP) secteur privé", "alias": "", "valeur": "En 2023, le salaire mensuel moyen en équivalent temps plein (EQTP) dans le secteur privé est de 2 730 euros, nets de cotisations et contributions sociales."},
    {"cle": "salaire mensuel moyen en équivalent temps plein (EQTP) secteur public", "alias": "", "valeur": "Dans la fonction publique, tous statuts confondus, un salarié gagne en moyenne 2 650 euros nets par mois en EQTP en 2023."},
    {"cle": "revenus non salariés", "alias": "", "valeur": "En 2023, hors agriculture, les non-salariés classiques (micro-entrepreneurs exclus) retirent en moyenne 4 040 euros par mois de leur activité non salariée. Cette moyenne recouvre de fortes disparités selon la nature des emplois."},
    {"cle": "salaires horaires", "alias": "", "valeur": "Au premier trimestre 2026, les salaires horaires augmentent de 0,3 % sur le trimestre et de 2,0 % sur un an"},
    {"cle": "coût horaire du travail", "alias": "Indice du coût du travail – ICT", "valeur": "Au premier trimestre 2026, le coût horaire du travail (salaires, cotisations et taxes, déduction faite des exonérations et subventions) de l'ensemble du secteur marchand non agricole (hors services aux ménages) freine significativement, dans le sillage des salaires : +0,5 % sur le trimestre et + 2,3 % sur un an."},
    {"cle": "création entreprises", "alias": "", "valeur": "En 2025, 1 165 800 entreprises ont été créées en France, dont 758 500 sous forme d'entrepreneurs individuels ayant adopté le régime de la microentreprise (micro-entrepreneurs)."},
    {"cle": "défaillances d'entreprises", "alias": "", "valeur": "En 2025, 68 872 unités légales ont été en situation de défaillance."},
    {"cle": "entreprises marchandes non agricoles et non financières en France", "alias": "", "valeur": "En 2023, en France, les secteurs marchands non agricoles et non financiers (incluant toutefois les exploitations forestières, les auxiliaires de services financiers et d'assurance et les holdings) comptent 5,2 millions d'entreprises. Ces entreprises emploient 15,9 millions de salariés en équivalent temps plein (EQTP)."},
    {"cle": "exploitations agricoles", "alias": "", "valeur": "Dans le secteur agricole, l'usage est de compter plutôt des exploitations agricoles ; en 2023, la France métropolitaine en compte 349 600 et la main d'œuvre agricole s'élève à 663 200 EQTP."},
    {"cle": "commerce", "alias": "", "valeur": "En 2023, le commerce rassemble 739 128 entreprises. Elles réalisent un chiffre d'affaires de 1 728 milliards d'euros et dégagent une valeur ajoutée (VA) de 272 milliards d'euros. Fin 2024, 3,4 millions de personnes occupent un emploi salarié dans le commerce."},
    {"cle": "industrie", "alias": "", "valeur": "En 2023, l'industrie rassemble 322 386 entreprises. Elles réalisent un chiffre d'affaire de 1 544 milliards d'euros et dégagent une valeur ajoutée (VA) de 368 milliards d'euros. Fin 2024, 3,3 millions de personnes occupent un emploi salarié dans l'industrie."},
    {"cle": "construction", "alias": "", "valeur": "En 2023, la construction rassemble 587 898 entreprises. Elles réalisent un chiffre d'affaires de 405 milliards d'euros et dégagent une valeur ajoutée (VA) de 128 milliards d'euros. Fin 2024, 1,5 million de personnes occupent un emploi salarié dans la construction."},
    {"cle": "services", "alias": "", "valeur": "En 2023, les services principalement marchands non financiers comptent plus de 2,3 millions d'entreprises. Ces entreprises réalisent un chiffre d'affaires de 995 milliards d'euros et dégagent une valeur ajoutée (VA) de 475 milliards d'euros. Fin 2024, 7,5 millions de personnes (y compris les intérimaires) occupent un emploi salarié dans les services principalement marchands non financiers."},
    {"cle": "transports", "alias": "", "valeur": "En 2023, les transports et l'entreposage rassemblent 193 101 entreprises. Elles réalisent un chiffre d'affaires de 267 milliards d'euros et dégagent une valeur ajoutée (VA) de 102 milliards d'euros. Fin 2024, 1,5 million de personnes occupent un emploi salarié dans les transports et l'entreposage."},
    {"cle": "entreprises de l'économie sociale", "alias": "", "valeur": "Les entreprises de l'économie sociale se caractérisent par leur famille de l'économie sociale, à la fois privé et à caractère essentiellement non lucratif. En 2022, elles représentent 9,8 % de l'emploi salarié total en équivalent temps plein. Les associations emploient 73 % de ce volume de travail salarié ; 14 % est employé par les coopératives, 6 % par les mutuelles, 5 % par les fondations et 3 % par les autres organismes privés à but non-lucratif."}
    {"cle": "Population quartiers prioritaires de la politique de la ville", "alias": "QPV", "valeur": "Les quartiers prioritaires de la politique de la ville (QPV) tels que définis par le décret n° 2015-1138 du 14 septembre 2015 regroupent 7,9 % de la population en 2020."},
    {"cle": "Population unités urbaines", "alias": "", "valeur": "Les unités urbaines rassemblent toujours plus d'habitants. En 2022, en France métropolitaine, elles représentent 78,8 % de la population, soit 51,9 millions d'habitants. À l'exception de l'unité urbaine de Paris qui concentre près de 11 millions d'habitants, les 10 plus grandes unités urbaines françaises comptent chacune entre 0,5 et 2 millions d'habitants."},
    {"cle": "mode déplacement domicile travail", "alias": "", "valeur": "Pour se rendre au travail, les personnes en emploi se déplacent majoritairement en voiture ou en deux-roues motorisés (71 % en 2022). 15 % des personnes en emploi empruntent les transports en commun."},
    {"cle": "dépense nationale protection de l'environnement", "alias": "", "valeur": "En 2022, la dépense nationale en faveur de la protection de l'environnement s'élève à 63,7 milliards d'euros (Md€). Elle est dédiée à la protection de l'air, de la biodiversité et des paysages, la collecte et traitement des déchets, la protection et dépollution des sols et des eaux, la lutte contre le bruit et d'autres activités de protection de l'environnement (frais de fonctionnement de l'administration publique et des opérateurs chargés des questions environnementales notamment). Les entreprises sont les principaux financeurs des dépenses de protection de l'environnement (22,6 Md€, soit 35 %), devant les administrations publiques (État et ses ministères, collectivités locales, organismes publics) (22,2 Md€, soit 35 %) et les ménages (18,1 Md€, soit 28 %)."},
    {"cle": "indice de référence des loyers", "alias": "IRL", "valeur": "Au deuxième trimestre 2026, l'indice de référence des loyers s'établit à 148,37. Sur un an, il augmente de 1,15 % après +0,78 % au trimestre précédent."},
    {"cle": "indice des loyers commerciaux", "alias": "ILC", "valeur": "Au premier trimestre 2026, l'indice des loyers commerciaux s'établit à 135,26. Sur un an, il baisse de 0,45 % (après -0,50 % au trimestre précédent)."},
    {"cle": "indice des loyers des activités tertiaires", "alias": "ILAT", "valeur": "Au premier trimestre 2026, l'indice des loyers des activités tertiaires s'établit à 137,42. Sur un an, il augmente de 0,09 % (après -0,06 % au trimestre précédent)."},
    {"cle": "indice du coût de la construction", "alias": "ICC", "valeur": "L'indice du coût de la construction (ICC) s'établit à 2 084 au premier trimestre 2026. Il est en hausse de 1,26 % sur un trimestre (après +0,10 % au trimestre précédent). Sur un an, il baisse de 2,89 % (après -2,37 % au trimestre précédent)."},
    {"cle": "index du bâtiment tous corps d'état", "alias": "BT01 ; index bâtiment BT01", "valeur": "En mai 2026, l'index Bâtiment BT01 « Tous corps d'état » s'établit à 137,9, en référence 100 en 2010."},
    {"cle": "index général des travaux publics", "alias": "TP01 ; index travaux publics TP01", "valeur": "En mai 2026, l’index Travaux publics TP01 « Index général tous travaux » s’établit à 140,4, en référence 100 en 2010."},
    {"cle": "index ingénierie", "alias": "ING ; indice ING", "valeur": "En mai 2026, l’index divers de la construction ING « Ingénierie » s’établit à 138,3, en référence 100 en 2010."},
]
