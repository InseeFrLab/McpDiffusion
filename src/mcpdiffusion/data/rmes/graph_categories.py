"""The families INSEE's named graphs are grouped into.

Static reference data only, like the other tables in this package: no classes and no behaviour.
`services/rmes/graph_taxonomy.py` turns these entries into matchers, and `GraphCategoryChoice` in
`models/rmes.py` is derived from their keys, so a family cannot exist in one place and not another.

A family matches a graph path by one of two tests:
  "prefixes" -- the path starts with any of them
  "paths"    -- the path equals any of them

Order matters twice: the first matching family wins, and this is the order they are reported in.
"""

CATEGORY_DEFINITIONS: list[dict] = [
    {
        "key": "qualite_rapports",
        "label": "Rapports qualite",
        "description": (
            "Un graphe par operation statistique documentee (sdmx-mm:MetadataReport), structure "
            "selon le standard europeen SIMS. Contient les dimensions qualite (pertinence, "
            "precision, actualite, coherence...) sous forme de sdmx-mm:ReportedAttribute. Tous ces "
            "graphes ont un schema identique."
        ),
        "prefixes": ["qualite/rapport/"],
    },
    {
        "key": "qualite_referentiels",
        "label": "Referentiels qualite",
        "description": (
            "Vocabulaire SIMS-FR (simsv2fr), documents annexes (documents) et referentiel "
            "territorial (territoires) associes aux rapports qualite."
        ),
        "paths": ["qualite/documents", "qualite/simsv2fr", "qualite/territoires"],
    },
    {
        "key": "codes_concepts_generiques",
        "label": "Concepts generiques de codification",
        "description": (
            "Concepts transverses qualifiant des operations ou nomenclatures (Frequence, Langue, "
            "ModeCollecte, UniteEnquetee, CategorieSource, StatutEnquete...) et notes explicatives "
            "xkos. Ce n'est PAS une nomenclature metier -- voir 'nomenclatures' pour "
            "NAF/PCS/COICOP/etc."
        ),
        "paths": ["codes", "codes/nomenclatures"],
    },
    {
        "key": "nomenclatures",
        "label": "Nomenclatures (classifications officielles)",
        "description": (
            "Nomenclatures statistiques officielles et leurs versions successives : activites "
            "(NAF/NAFR), produits (CPF), professions et categories socioprofessionnelles "
            "(PCS/PCSESE), consommation (COICOP), categories juridiques (CJ), emplois (EAP/EMB par "
            "annee), tables de correspondance entre versions (ex: nafr2-cpfr21)."
        ),
        "prefixes": ["codes/"],
    },
    {
        "key": "operations_statistiques",
        "label": "Operations statistiques",
        "description": (
            "Catalogue des operations (StatisticalOperation), series et familles "
            "d'enquetes/collectes de l'Insee. C'est la cible (sdmx-mm:target) de chaque rapport "
            "qualite."
        ),
        "paths": ["operations"],
    },
    {
        "key": "demographie",
        "label": "Demographie",
        "description": "Populations legales par annee (popleg<annee>).",
        "prefixes": ["demo/"],
    },
    {
        "key": "geographie",
        "label": "Geographie",
        "description": "Code officiel geographique (COG) : communes, decoupages administratifs.",
        "prefixes": ["geo/"],
    },
    {
        "key": "organisations",
        "label": "Organisations",
        "description": (
            "Organismes producteurs de statistiques (services statistiques ministeriels...) et "
            "unites organisationnelles internes de l'Insee."
        ),
        "prefixes": ["organisations"],
    },
    {
        "key": "concepts",
        "label": "Concepts et definitions statistiques",
        "description": "Themes statistiques et definitions de notions utilisees dans les publications.",
        "prefixes": ["concepts"],
    },
    {
        "key": "produits",
        "label": "Produits / indicateurs statistiques",
        "description": "Indicateurs statistiques publies (StatisticalIndicator).",
        "paths": ["produits"],
    },
    {
        "key": "catalogue",
        "label": "Catalogue DCAT",
        "description": "Metadonnees de catalogage (dcat:Dataset, dcat:CatalogRecord).",
        "paths": ["catalogue"],
    },
    {
        "key": "ontologies",
        "label": "Ontologies / schema RDF",
        "description": (
            "Definitions de classes et proprietes OWL/RDFS (def/base, def/geo, def/demo) qui "
            "structurent les autres graphes. A consulter pour comprendre le schema d'un graphe de "
            "donnees, pas pour y chercher des donnees elles-memes."
        ),
        "prefixes": ["def/"],
    },
]

# Matches anything, so it is tried last and never declares a test of its own.
# Keeps its French key: `category` is part of the tool output.
FALLBACK_CATEGORY_DEFINITION: dict = {
    "key": "autre",
    "label": "Autre / non categorise",
    "description": (
        "Graphes ne correspondant a aucune famille connue ci-dessus. Categorie de secours : si "
        "l'INSEE ajoute de nouveaux graphes sans mise a jour de ce serveur, ils apparaissent "
        "ici plutot que d'etre mal classes."
    ),
}
