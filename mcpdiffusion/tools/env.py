from datetime import datetime
from typing import Literal


CURRENT_YEAR = datetime.now()
DATE_CURRENT_YEAR = f"{CURRENT_YEAR}"


GET_DATASET={
    "tool_name":"get_MELODI_datasets",
    "tool_description":"Retrieve a filtered set of observations from a Melodi dataset. The Melodi API holds official, high‑granularity statistics (prices, mortality, names, etc.). You must first identify the exact dataset and the relevant modality codes, then apply column‑level filters (e.g., product code, geographic code, time period) to obtain only the observations needed for the answer. The response includes dimensions, attributes and the numeric measure (with unit).",
    "tool_metadata":{"version":"2.0","author":"mirlon"}
}

SEARCH_DATASET={
    "tool_name":"search_MELODI_datasets",
    "tool_description":"Search the catalogue of INSEE Melodi datasets. Each dataset has a unique identifier and the tool maps a natural‑language query to internal metadata to return the most appropriate dataset. The matching is purely lexical, so you must provide a clear, explicit query and optionally augment it with French synonyms via the french_notions parameter. Example: query = 'Mort Paris', french_notions = 'mortalité décès' → matches dataset DS_DECES_MORTALITE_SERIES.\nWhen the user asks for a precise variable (price of a specific product, mortality by region, frequency of a name, etc.), start with this tool to locate the correct dataset.",
    "tool_metadata":{"version":"3.0","author":"mirlon"}
}

SEARCH_COLUMNS={
    "tool_name":"search_MELODI_modalities",
    "tool_description":"Given a Melodi dataset and one or more column identifiers, rank the most pertinent modalities (codes/labels) for a free‑text query. Provide the dataset identifier, the column IDs to explore, and a natural‑language query describing the desired modality (e.g., 'côte de bœuf', 'Île‑de‑France', 'female Maria'). The tool returns the matching codes, their French/English labels and a relevance score. Use this step to obtain the exact code(s) required for filtering in get_MELODI_datasets.",
    "tool_metadata":{"version":"3.0","author":"mirlon"}
}

GET_DOCUMENTS={
    "tool_name":"get_insee_documents",
    "tool_description":                "Retrieve and parse data from the INSEE documents. The output will contain explanations and analysis backed by data on a topic. The tool needs a list of identifier of products."
                "Use this tool ONLY when you have one or more explicit url.\n"
                "Tool reaches the insee webpages and may not always succeed because of the diversity of products. \n"
                "Url may have the form /fr/statistiques/4277658?sommaire=4318291 or /fr/statistiques/4277658."
                "The url **must** start with / then language then product type then identifier."
                "The include_sommaire option retrieves linked publications. It must be used once to discover the structure then turned off for requests on the same page.",
    "tool_metadata":{"version": "4.0", "author": "mirlon"}
    }


SEARCH_INSEE_PRODUIT={
    "tool_name":"search_insee_documents",
    "tool_description":f"Search the INSEE catalogue of official statistical publications (reports, studies, “Chiffres‑clés”, “L’essentiel sur…”, Insee Première, etc.).  \n"
"Use this tool when the user needs more than the brief, up‑to‑date figures displayed on the INSEE home page – e.g.:\n"

"* detailed tables or historic series,\n"
"* regional, departmental or municipal breakdowns,\n"
"* methodological notes, definitions, or full‑text analysis,\n"
"* specific thematic studies (demography, labour market, public finances, environment, …).\n"

"How the search works  \n"
"- Provide a natural‑language query enriched with synonyms, related concepts and, when possible, a target year and/or geography.  \n"
"- Set the appropriate filters to sharpen the results:  \n"
"  • **chiffre_clef = true** for key‑figure extracts (inflation, chômage, etc.).  \n"
"  • **geo_keyword** and **geo_niveau** (REG, DEP, COM, COMPRD, …) for territorial queries.  \n"
"  • **theme** to limit the search to a top‑level INSEE theme (e.g., “Démographie”, “Marché du travail – Salaires”).  \n"
"  • **year_of_reference** to focus on a specific publication year.\n"  
"- The tool returns a list of matching publications, each identified by its INSEE serial number (idproduit) together with a short title, subtitle and relevance score.\n"

"Important notes  \n"
"- **Rapid Releases (Informations rapides)** are *excluded*; they are short, recurring releases meant for the home‑page widgets.  \n"
"- The catalogue covers only the detailed, peer‑reviewed INSEE documents; use the home‑page tool for quick indicators.  \n"
"- The field **chiffre_clef** is the preferred entry point for “key‑figure” searches (e.g., inflation, taux de chômage).\n"  
"- The **geo_niveau** values include COMPRD (all departments and regions), DEP, REG, COM, INTER, FRANCE, etc., enabling precise territorial filtering.  \n"
"Example  \n"
"User: “Quel est le population de la Bretagne ?”  \n"
"Query to the tool:  \n"
"  - query = “Bretagne”  \n"
"  - chiffre_clef = true  \n"
"  - geo_keyword = “Bretagne” \n" 
"  - geo_niveau = REG\n"  

"Result: the publication “L’essentiel sur la Bretagne” (or the corresponding “Chiffres‑clés” file) appears in the list.\n"
"Current date is {CURRENT_YEAR}.",
    "tool_metadata":{"version": "4.0", "author": "mirlon"}
    }

SEARCH_INSEE_CONJ={
    "tool_name":"search_insee_conjoncture",
    "tool_description":f"Searches Insee Rapid Releases (Informations rapides): short, recurring publications reporting the latest official monthly, quarterly or annual results for major economic and social indicators. They provide recent figures, tables and concise factual commentary on topics such as prices, employment, business conditions, production, housing, wages and national accounts. Prefer the latest relevant edition unless the user requests a specific past period.This tool is a search engine maping queries to publications words. The best way to use this tool is to provide many words, synonyms and related notions. The specific filters on date and geography **must** be used in order to get better results. Current date is {CURRENT_YEAR}.",
    "tool_metadata":{"version": "2.0", "author": "mirlon"}
    }

SEARCH_INSEE_HOMEPAGE={
    "tool_name":"get_insee_homepage",
    "tool_description":f"Retrieve the INSEE home page that showcases the latest key indicators published by the institute.\n"  
"Use this tool **first** whenever the user asks for a basic, **up‑to‑date** statistic such as population, inflation, unemployment, GDP growth, etc. Never use this tool when the user ask for statistics from previous years\n"
"What the endpoint returns:\n" 
"- A concise list of “main indicators” (value, short description, and a direct link to the underlying official product).\n"
"- Short explanatory notes attached to each indicator.\n " 
"- A selection of recent articles for further reading.\n"

"Why it is the preferred approach:\n"
"- Provides the most recent official figure instantly, without the overhead of searching through individual documents.\n"
"- Guarantees that the answer is consistent with the latest published data.\n"
"- Supplies the link to the full statistical release so the user can drill down for detailed tables or methodology if needed.\n"

"**Workflow recommendation** \n"
"1. Call this endpoint for generic questions. \n"
"2. Present the indicator value and its brief description, along with the link to the full report. \n"
"3. Only if the user explicitly requests deeper tables, historic series, or methodological details, follow up with a document‑search (e.g., `1_search_insee_documents` or `1_get_insee_documents`). \n"

"Current date is {CURRENT_YEAR}.\n",
    "tool_metadata":{"version": "1.0", "author": "mirlon"}
    }


INSEE_GEO = Literal[
    "COM",
    "DEP",
    "REG",
    "INTER",
    "COMPRD",
    #"FE",
    "FRANCE",
    #"FE_HORS_MAYOTTE",
    #"UU2010 IRIS EPCI AAV2020 ZE2010 COLLECTIVITE_OUTRE_MER ARR"
]

DICT_GEO ={
    "COMMUNE":"COM",
    "DEPARTEMENT":"DEP",
    "REGION":"REG",
    "INTERNATIONAL":"INTER",
    "INTER REGION":"COMPRD",
    "FRANCE":"FRANCE"
}

INSEE_CONTENU =Literal[
    "cogRefonte",
    "l'insee",
    "metadonnees",
    "services",
    "actualiteSSM",
    "statistiques",
    "communiquesDePresse",
    "methodes",
    "cog",
    "source"
                     ] 



INSEE_THEME_NIV1=Literal[
#"Méthodes",
"Démographie",
"Revenus – Pouvoir d'achat – Consommation",
"Conditions de vie – Société",
"Marché du travail – Salaires",
"Économie – Conjoncture – Comptes nationaux",
"Développement durable – Environnement",
"Entreprises",
"Secteurs d'activité",
"Territoires, villes et quartiers"
]

KEYS_THEME_NIV1={
"Démographie":0,
"Conditions de vie – Société":6,
"Marché du travail – Salaires":20,
"Économie – Conjoncture – Comptes nationaux":27,
"Entreprises":37,
"Secteurs d'activité":44, #48,53,60 sont des sous thème de niveau2 A integrer
"Territoires, villes et quartiers":68,
"Développement durable – Environnement":74,
"Revenus – Pouvoir d'achat – Consommation":80,
"Méthodes":86,
}

WIP_PRODUIT_THEME = Literal[
    'Conjoncture', 
    'Économie générale (inflation, PIB, dette,...)', 
    'Emploi – Population active', 
    "Revenus – Niveaux de vie – Pouvoir d'achat", 
    "Caractéristiques de l'industrie", 
    'Construction', 
    'Caractéristiques des entreprises', 
    'Évolution et structure de la population', 
    'Consommation et équipement des ménages', 
    'Caractéristiques du commerce', 
    'Dynamique des territoires', 
    'Logement', 
    'Commerce de détail', 
    'Caractéristiques des services', 
    'Démographie et créations des entreprises', 
    'Industrie manufacturière', 
    'Tourisme', 
    'Chômage', "Salaires et revenus d'activité", 
    'Agriculture', 
    'Pauvreté – Précarité', 'Commerce de gros', 
    'Services par activités', 
    'Commerce extérieur', 
    'Énergie', 'Éducation – Formation – Compétences', 
    'Égalité femmes-hommes', 
    'Mobilités - Déplacements - Frontaliers', 
    'Villes et quartiers', 
    'Transports', 
    'Société – Vie sociale – Élections', 
    'Comptes nationaux trimestriels', 
    'Couples – Familles – Ménages', 
    'Environnement', 
    'Santé – Handicap – Dépendance', 
    'Naissances – Fécondité', 
    'Équipements et services à la population', 
    'Décès – Mortalité – Espérance de vie', 
    'Développement durable', 
    'Mondialisation, compétitivité et innovation', 
    'Finances publiques', 
    'Loisirs – Culture', 
    'Comptes nationaux annuels', 
    'Étrangers – Immigrés', 
    'Protection sociale – Retraites', 
    'Patrimoine', 
    'Sécurité – Justice', 
    'Industrie agroalimentaire', 
    'Industrie automobile', 'Méthodes', 
    'Économie sociale et solidaire'
    ]

WIP_PRODUIT_COLLECTION= Literal[
    'Informations rapides',
    'Insee Analyses',
    'Insee Conjoncture',
    'Insee Flash',
    'Insee Références',
    #'Fichier détail',
    'Insee Focus',
    'Insee Dossier',
    'Insee Première'
]

THEME_CONJ= Literal[
"Indice de la production industrielle", 
"Enquête mensuelle de conjoncture dans l'industrie",
"Enquête trimestrielle de conjoncture dans l'industrie",
"Chiffre d'affaires dans l'industrie et la construction",
"Indices des commandes en valeur reçues dans l'industrie",
#"Construction de logements",
"Enquête mensuelle de conjoncture dans l'industrie du bâtiment",
"Enquête trimestrielle dans la promotion immobilière",
"Enquête trimestrielle dans les travaux publics",
"Enquête trimestrielle dans l'artisanat du bâtiment",
"Enquête mensuelle de conjoncture dans le commerce de détail et le commerce et la réparation automobiles",
"Enquête mensuelle de conjoncture dans les services",
"Volume des ventes dans le commerce de détail et les services personnels",
"Fréquentation touristique dans les hôtels, campings et autres hébergements collectifs touristiques",
"Chiffre d'affaires dans le commerce de gros et divers services aux entreprises",
"Enquête sur les investissements dans l'industrie",
"Créations d'entreprises",
"Enquête de trésorerie dans l'industrie",
"Volume des ventes dans le commerce",
"Défaillances d'entreprises (parution arrêtée aux résultats de juillet 2012)",
"Indice du coût horaire du travail révisé - Tous salariés (ICHT, ICHTrev-TS) - Publication arrêtée depuis le 06/10/2023",
"Estimation flash de l'emploi salarié",
"Emploi salarié",
"Consommation de soins et biens médicaux (CSBM)",
"L'emploi dans la fonction publique",
"Prestations et ressources de protection sociale",
"Dépenses de consommation des ménages en biens",
"Enquête mensuelle de conjoncture auprès des ménages",
"Indice de traitement brut dans la fonction publique d’État - grille indiciaire",
"Salaires de base – Comparaison France-Allemagne",
"Les salaires dans la fonction publique",
"Immatriculations de véhicules neufs",
"Réserves officielles de change",
"Réserves nettes de change",
"Emploi et taux de chômage localisés (par région et département)",
"Balance des paiements",
"Notes et Points de conjoncture nationaux",
"Indices de prix de production et d'importation de l'industrie",
"Indice de référence des loyers",
"Prix à la consommation - moyennes annuelles",
"Indices des prix agricoles",
"Indice du coût de la construction",
"Indice des loyers commerciaux",
"Indice des loyers des activités tertiaires",
"Index bâtiment, travaux publics et divers de la construction",
"Indices des coûts de production dans la construction",
"Indice des prix des logements neufs et anciens",
"Indices des prix des logements anciens",
"Indices des prix de production des services",
"Situation mensuelle budgétaire de l'Etat",
"Indice de production dans les services",
"Comptes nationaux trimestriels - résultats détaillés",
"Comptes nationaux des administrations publiques - premiers résultats",
"Enquête bimestrielle de conjoncture dans le commerce de gros",
"Indice du coût du travail (ICT) - Résultats détaillés",
"Prix des énergies et des matières premières importées",
"Dette trimestrielle de Maastricht des administrations publiques",
"Indice des prix à la consommation - résultats définitifs",
"Comptes nationaux trimestriels - deuxième estimation",
"Indice des prix à la consommation - résultats provisoires",
"Comptes nationaux trimestriels - première estimation",
"Conjoncture régionale",
"Enquête annuelle crédit-bail",
"Indice des prix d’entretien-amélioration des bâtiments",
"Indices des loyers d'habitation",
"Comptes nationaux annuels - révision des principaux agrégats",
"Résultats du commerce extérieur - Importations et exportations de biens",
"Emploi salarié, salaires de base et durée du travail (résultats définitifs)",
"Emploi salarié, salaires de base et durée du travail (résultats provisoires)",
"Climat des affaires",
"Construction de locaux",
"Commercialisation de logements neufs - Ventes aux particuliers et ventes aux institutionnels",
"Chiffre d'affaires des grandes surfaces alimentaires (parution arrêtée aux résultats de décembre 2022)",
"Chômage au sens du BIT et indicateurs sur le marché du travail (résultats de l'enquête Emploi)",
"Indice du coût du travail (ICT) - Estimation flash",
"Recettes fiscales de l’État",
"Les inscrits à France Travail",
"Indice des prix dans la grande distribution (parution arrêtée aux résultats de décembre 2025)"
]


DICT_THEME_CONJ = {
    "Industrial production and activity": [
        "Indice de la production industrielle ",
        "Enquête mensuelle de conjoncture dans l'industrie",
        "Enquête trimestrielle de conjoncture dans l'industrie",
        "Chiffre d'affaires dans l'industrie et la construction",
        "Indices des commandes en valeur reçues dans l'industrie",
        "Enquête sur les investissements dans l'industrie",
        "Enquête de trésorerie dans l'industrie"
    ],

    "Construction and building sector": [
        "Enquête mensuelle de conjoncture dans l'industrie du bâtiment",
        "Enquête trimestrielle dans les travaux publics",
        "Enquête trimestrielle dans l'artisanat du bâtiment",
        "Construction de locaux",
        "Index bâtiment, travaux publics et divers de la construction",
        "Indices des coûts de production dans la construction",
        "Indice des prix d’entretien-amélioration des bâtiments",
        "Indice du coût de la construction"
    ],

    "Housing and real estate": [
        "Enquête trimestrielle dans la promotion immobilière",
        "Indice de référence des loyers",
        "Indice des loyers commerciaux",
        "Indice des loyers des activités tertiaires",
        "Indices des loyers d'habitation",
        "Indice des prix des logements neufs et anciens",
        "Indices des prix des logements anciens",
        "Commercialisation de logements neufs - Ventes aux particuliers et ventes aux institutionnels"
    ],

    "Retail, wholesale and services": [
        "Enquête mensuelle de conjoncture dans le commerce de détail et le commerce et la réparation automobiles",
        "Enquête mensuelle de conjoncture dans les services",
        "Enquête bimestrielle de conjoncture dans le commerce de gros",
        "Volume des ventes dans le commerce de détail et les services personnels ",
        "Volume des ventes dans le commerce",
        "Chiffre d'affaires dans le commerce de gros et divers services aux entreprises",
        "Indice de production dans les services",
        "Chiffre d'affaires des grandes surfaces alimentaires (parution arrêtée aux résultats de décembre 2022)"
    ],

    "Business demographics and confidence": [
        "Créations d'entreprises",
        "Défaillances d'entreprises (parution arrêtée aux résultats de juillet 2012)",
        "Climat des affaires",
        "Notes et Points de conjoncture nationaux",
        "Conjoncture régionale"
    ],

    "Employment, unemployment and labour market": [
        "Estimation flash de l'emploi salarié",
        "Emploi salarié",
        "Emploi et taux de chômage localisés (par région et département)",
        "Emploi salarié, salaires de base et durée du travail (résultats définitifs)",
        "Emploi salarié, salaires de base et durée du travail (résultats provisoires)",
        "Chômage au sens du BIT et indicateurs sur le marché du travail (résultats de l'enquête Emploi)",
        "Les inscrits à France Travail"
    ],

    "Wages and labour costs": [
        "Indice du coût horaire du travail révisé - Tous salariés (ICHT, ICHTrev-TS) - Publication arrêtée depuis le 06/10/2023",
        "Indice du coût du travail (ICT) - Résultats détaillés",
        "Indice du coût du travail (ICT) - Estimation flash",
        "Salaires de base – Comparaison France-Allemagne"
    ],

    "Public sector employment and pay": [
        "L'emploi dans la fonction publique",
        "Indice de traitement brut dans la fonction publique d’État - grille indiciaire",
        "Les salaires dans la fonction publique"
    ],

    "Households, consumption and health": [
        "Consommation de soins et biens médicaux (CSBM)",
        "Prestations et ressources de protection sociale",
        "Dépenses de consommation des ménages en biens",
        "Enquête mensuelle de conjoncture auprès des ménages "
    ],

    "Inflation and producer prices": [
        "Prix à la consommation - moyennes annuelles",
        "Indice des prix à la consommation - résultats définitifs",
        "Indice des prix à la consommation - résultats provisoires",
        "Indices de prix de production et d'importation de l'industrie",
        "Indices des prix de production des services ",
        "Indices des prix agricoles",
        "Prix des énergies et des matières premières importées",
        "Indice des prix dans la grande distribution (parution arrêtée aux résultats de décembre 2025)"
    ],

    "National accounts and public finance": [
        "Comptes nationaux trimestriels - première estimation",
        "Comptes nationaux trimestriels - deuxième estimation",
        "Comptes nationaux trimestriels - résultats détaillés",
        "Comptes nationaux annuels - révision des principaux agrégats",
        "Comptes nationaux des administrations publiques - premiers résultats",
        "Situation mensuelle budgétaire de l'Etat",
        "Dette trimestrielle de Maastricht des administrations publiques",
        "Recettes fiscales de l’État"
    ],

    "External trade and financial accounts": [
        #"Balance des paiements", BDF
        #"Résultats du commerce extérieur - Importations et exportations de biens", DOUANES
        #"Réserves officielles de change ", DGTrésor
        #"Réserves nettes de change" DGTrésor
    ],

    "Transport and tourism": [
        "Immatriculations de véhicules neufs",
        "Fréquentation touristique dans les hôtels, campings et autres hébergements collectifs touristiques"
    ],

    "Business financing": [
        "Enquête annuelle crédit-bail"
    ]
}

DICT_KV = [
#{'cle': 'cle', 'alias': 'alias', 'valeur': 'valeur'},
{'cle': 'estimation de population France', 'alias': '', 'valeur': 'Au 1er janvier 2026, la population  r�sidant en France est estim�e � 69,1 millions d�habitants,'}, {'cle': 'population l�gale France', 'alias': '', 'valeur': 'Au 1er�janvier�2023, la population de la France hors Mayotte s��tablit officiellement � 68�094�000�habitants '}, {'cle': 'immigr�s France', 'alias': '', 'valeur': "En�2025, 8,0�millions d'immigr�s vivent en France, soit 11,6�% de la population totale. "}, {'cle': 'population �trang�re France', 'alias': '', 'valeur': "En�2025, la population �trang�re vivant en France s'�l�ve � 6,3�millions de personnes, soit 9,1�% de la population totale. "},
{'cle': 'naissances France', 'alias': '', 'valeur': 'En�2025, le nombre de naissances en France est estim� � 645�000�, soit une baisse de -2,1% par rapport �2024 '}, {'cle': 'indicateur conjoncturel de f�condit�', 'alias': '', 'valeur': 'En 2025, l�indicateur conjoncturel de f�condit� (ICF) continue de diminuer. Il s��tablit � 1,56�enfant par femme (1,53�en France m�tropolitaine), apr�s 1,61�en 2024 (1,58�en France m�tropolitaine). '}, {'cle': 'd�c�s France', 'alias': '', 'valeur': 'En 2025, le nombre de d�c�s en France est estim� � 651�000, en hausse de 1,5�% par rapport � 2024, apr�s +0,3�% entre 2023 et 2024 (en tenant compte du fait que 2024 est une ann�e bissextile) '}, {'cle': 'esp�rance de vie France', 'alias': '', 'valeur': 'En 2025, l�esp�rance de vie � la naissance s��l�ve � 85,9�ans pour les femmes et � 80,3�ans pour les hommes. Elle augmente en 2025, de +0,1�an pour les femmes comme pour les hommes, pour atteindre un niveau historiquement �lev� '}, {'cle': 'mariages France', 'alias': '', 'valeur': 'En 2025, le nombre de mariages c�l�br�s en France est estim� � 251 000, dont 244 000 entre personnes de sexe diff�rent et 7 000 entre personnes de m�me sexe. Le nombre de mariages augmente de 1,4 % par rapport � 2024, apr�s +2,7 % entre 2023 et 2024 (en tenant compte du fait que 2024 est une ann�e bissextile), alors que la tendance �tait plut�t � la baisse avant la crise sanitaire'},
{'cle': 'm�nages France', 'alias': '', 'valeur': 'En�2023, la France hors Mayotte compte 31,3�millions de m�nages '},
{'cle': 'divorces France', 'alias': '', 'valeur': "128043 divorces en 2016. Note : jusqu'en 2016, les divorces �taient des d�cisions de justice prononc�es par un juge aux affaires familiales. � partir de 2017, suite � la loi n� 2016-1547 du 18 novembre 2016 de modernisation de la justice du XXIe si�cle, les proc�dures de divorces peuvent �galement �tre enregistr�es par un notaire et il n�est pas possible, pour l�instant de r�cup�rer les donn�es de divorces enregistr�s par les notaires. C�est pourquoi les donn�es statistiques compl�tes sur les divorces ne sont plus disponibles � partir de 2017. Plus de d�tail aupr�s du Service de la statistique, des �tudes et de la recherche (SSER) "}, {'cle': 'inflation', 'alias': 'Indice des prix � la consommation � IPC ', 'valeur': 'En juin 2026, les prix � la consommation (IPC) augmentent de 1,8 % sur un an. Sur un mois, l�indice des prix � la consommation diminue de 0,3 %.'}, {'cle': 'Ch�mage BIT ', 'alias': '', 'valeur': 'Au premier trimestre 2026, le taux de ch�mage  en France (hors Mayotte) augmente de 0,2 point et atteint 8,1 % . Le nombre de ch�meurs est de  2,6 millions de personnes.'}, {'cle': 'emploi BIT', 'alias': '', 'valeur': 'En moyenne sur l�ann�e 2025, parmi les personnes �g�es de 15 � 64 ans vivant en France, 69,3 % sont en emploi au sens du Bureau international du travail (BIT) '}, {'cle': 'PIB trimestriel', 'alias': 'croissance trimestrielle', 'valeur': 'Au premier trimestre 2026, le produit int�rieur brut (PIB) en volume se replie l�g�rement (-0,1�%). '}, {'cle': 'PIB annuel', 'alias': 'croissance annuelle', 'valeur': 'En 2025, le PIB croit de 0,8�% en volume aux prix de l�ann�e pr�c�dente '}, {'cle': 'D�penses de consommation des m�nages en biens ', 'alias': '', 'valeur': 'En mai 2026, les d�penses de consommation des m�nages en biens rebondissent sur un mois (+0,5 % en volume apr�s -0,5 % en avril). Les volumes sont mesur�s aux prix de l�ann�e pr�c�dente cha�n�s (en milliards d�euros 2020) et corrig�s des variations\nsaisonni�res et des effets des jours ouvrables (CVS-CJO).'}, {'cle': 'Climat des affaires', 'alias': '', 'valeur': 'En juin 2026, l�indicateur synth�tique du climat des affaires, calcul� � partir des r�ponses des chefs d�entreprise des principaux secteurs d�activit� marchands rebondit tr�s l�g�rement, � 94, en de�� de son niveau moyen '}, {'cle': 'climat de l�emploi', 'alias': '', 'valeur': 'En juin 2026, L�indicateur du climat de l�emploi perd de nouveau trois points (apr�s arrondi) et s��tablit � 89, son niveau le plus bas depuis juin 2013 (hors crise sanitaire). '}, {'cle': 'production manufacturi�re', 'alias': 'Indice de la production industrielle � IPI', 'valeur': 'En mai 2026, apr�s deux mois de hausse, la production se replie nettement dans l�industrie manufacturi�re (-1,0�% apr�s +0,6�% en avril 2026). Dans l�ensemble de l�industrie, elle se replie aussi mais plus l�g�rement (-0,1�% apr�s +0,3�%). '}, {'cle': 'niveau de vie  ', 'alias': '', 'valeur': 'En 2024, en France m�tropolitaine, le niveau de vie m�dian de la population s��l�ve � 26 740 euros annuels. Il correspond � un revenu disponible de 2 228 euros par mois pour une personne seule et de 4 680 euros par mois pour un couple avec deux enfants de moins de 14 ans. Les 10 % de personnes les plus modestes ont un niveau de vie inf�rieur � 13 970 euros. Les 10 % les plus ais�es ont un niveau de vie au moins 3,5 fois sup�rieur, au-del� de 48 580 euros.'}, {'cle': 'pouvoir d�achat', 'alias': '', 'valeur': 'En�2025, le pouvoir d�achat du revenu disponible (RDB) des m�nages se replie de 0,4 % apr�s une hausse de 2,7 % en 2024. Ramen� au niveau individuel et en tenant compte de l��volution de la taille des m�nages, le pouvoir d�achat baisse de 0,7 % apr�s une hausse de 2,2 % en 2024'}, {'cle': 'balance commerciale', 'alias': '', 'valeur': 'En 2025, les exportations en volume restent soutenues (+2,3�% apr�s +3,2�% en 2024), tandis que les importations se redressent nettement (+2,8�% apr�s -0,6�%). De ce fait, les �changes ext�rieurs p�sent sur la croissance de l�activit� en 2025, � hauteur de -0,2�point de PIB, apr�s l�avoir fortement soutenue en 2023 et 2024. '}, {'cle': 'pauvret� mon�taire', 'alias': '', 'valeur': 'En�2024, 9,8�millions de personnes vivent avec un niveau de vie inf�rieur au seuil de pauvret� mon�taire, soit 15,4�% de la population vivant dans un logement ordinaire en France m�tropolitaine.'}, {'cle': 'patrimoine', 'alias': '', 'valeur': 'D�but�2024, la moiti� des m�nages vivant en France d�clarent un patrimoine brut sup�rieur � 205�100�euros. La moiti� la mieux dot�e en patrimoine brut poss�de collectivement 93�% de la masse totale de patrimoine. '}, {'cle': '�tat sant�', 'alias': '', 'valeur': 'En�2024, deux�tiers des personnes �g�es de 16�ans ou plus se d�clarent en bonne ou tr�s bonne sant�. � l�oppos�, pr�s de 10�% jugent leur �tat de sant� mauvais voire tr�s mauvais '}, {'cle': 'prestation handicap', 'alias': '', 'valeur': 'Selon leur �ge et leur situation, les personnes en situation de handicap ou de perte d�autonomie peuvent pr�tendre � diff�rentes prestations. Fin�2023, 44�000�personnes ont un droit ouvert � l�allocation compensatrice pour tierce personne�(ACTP) et 407�000�� la prestation de compensation du handicap�(PCH). Par ailleurs, 1,4�million de personnes de 60�ans ou plus ont per�u l�allocation personnalis�e d�autonomie�(APA) au titre du mois de d�cembre�2023 '}, {'cle': 'd�penses li�es � la culture ', 'alias': '', 'valeur': 'En�2025, les d�penses li�es � la culture, au sport et aux loisirs s��l�vent � 108�milliards�d�euros. Les services r�cr�atifs, sportifs et culturels rassemblent 45�% de ces d�penses.'}, {'cle': 'Parc de logements', 'alias': '', 'valeur': 'Au 1er�janvier�2025, la France hors Mayotte compte 38,4�millions de logements. 82,5�% des logements sont des r�sidences principales et 54,4�% des logements individuels (maisons) '}, {'cle': 'logements vacants', 'alias': '', 'valeur': 'Apr�s avoir fortement augment� entre 2005 et 2019, la part des logements vacants diminue, passant de 8,1�% en�2019 � 7,7�% en�2025�; en�2025, 3,0�millions de logements sont vacants. '}, {'cle': 'r�sidences secondaires ou  logements occasionnels', 'alias': '', 'valeur': 'Au 1er�janvier�2025, 3,8�millions de logements sont des r�sidences secondaires ou des logements occasionnels�; apr�s avoir augment� entre 2011 et 2017, leur part dans l�ensemble du parc est stable. '}, {'cle': 'm�nages sont propri�taires de leur r�sidence principale ', 'alias': '', 'valeur': 'Au 1er�janvier�2025, 57,4�% des m�nages sont propri�taires de leur r�sidence principale '}, {'cle': 'smic', 'alias': 'Salaire minimum interprofessionnel de croissance', 'valeur': 'Depuis le 1er janvier 2026, le Smic brut s��l�ve � 12,02 euros par heure, soit 1 823,03 euros par mois pour 151,67 heures de travail.'}, {'cle': 'salaire mensuel moyen en �quivalent temps plein�(EQTP)  secteur priv�', 'alias': '', 'valeur': 'En�2023, le salaire mensuel moyen en �quivalent temps plein�(EQTP) dans le secteur priv� est de 2�730�euros, nets de cotisations et contributions sociales '}, {'cle': 'salaire mensuel moyen en �quivalent temps plein�(EQTP)  secteur public', 'alias': '', 'valeur': 'Dans la fonction publique, tous statuts confondus, un salari� gagne en moyenne 2�650�euros nets par mois en EQTP�en�2023. '}, {'cle': 'revenus non salari�s', 'alias': '', 'valeur': 'En�2023, hors agriculture, les non-salari�s classiques (micro-entrepreneurs exclus) retirent en moyenne 4�040�euros par mois de leur activit� non salari�e. Cette moyenne recouvre de fortes disparit�s selon la nature de l�activit� exerc�e.'}, {'cle': 'salaires horaires', 'alias': '', 'valeur': 'Au premier trimestre 2026, les salaires horaires augmentent de 0,3 % sur le trimestre et de 2,0 % sur un an'}, {'cle': 'co�t horaire du travail', 'alias': '', 'valeur': 'Au premier trimestre 2026, le co�t horaire du travail (salaires, cotisations et taxes, d�duction faite des exon�rations et subventions) de l�ensemble du secteur marchand non agricole (hors services aux m�nages) freine significativement, dans le sillage des salaires�: +0,5�% sur le trimestre  et + 2,3 % sur un an'}, {'cle': 'cr�ation entreprises', 'alias': '', 'valeur': "En�2025, 1�165�800�entreprises ont �t� cr��es en France, dont 758�500�sous forme d'entrepreneurs individuels ayant adopt� le r�gime de la microentreprise (micro-entrepreneurs). "}, {'cle': 'd�faillances d�entreprises', 'alias': '', 'valeur': 'En�2025, 68�872�unit�s l�gales ont �t� en situation de d�faillance. '}, {'cle': 'entreprises marchandes non agricoles et non financi�res en France', 'alias': '', 'valeur': "En�2023, en France, les secteurs marchands non agricoles et non financiers (incluant toutefois les exploitations foresti�res, les auxiliaires de services financiers et d�assurance et les holdings) comptent 5,2�millions d'entreprises. Ces entreprises emploient 15,9�millions de salari�s en �quivalent temps plein�(EQTP). "}, {'cle': 'exploitations agricoles ', 'alias': '', 'valeur': 'Dans le secteur agricole, l�usage est de compter plut�t des exploitations agricoles�; en�2023, la France m�tropolitaine en compte 349 600 et la main d��uvre agricole s��l�ve � 663�200 EQTP. '}, {'cle': 'commerce', 'alias': '', 'valeur': 'En�2023, le commerce rassemble 739�128�entreprises. Elles r�alisent un chiffre d�affaires de 1�728�milliards d�euros et d�gagent une valeur ajout�e�(VA) de 272�milliards d�euros. Fin�2024, 3,4�millions de personnes occupent un emploi salari� dans le commerce. '}, {'cle': 'industrie', 'alias': '', 'valeur': 'En�2023, l�industrie rassemble 322�386�entreprises. Elles r�alisent un chiffre d�affaires de 1�544�milliards d�euros et d�gagent une valeur ajout�e�(VA) de 368�milliards d�euros. Fin�2024, 3,3�millions de personnes occupent un emploi salari� dans l�industrie.'}, {'cle': 'construction', 'alias': '', 'valeur': 'En�2023, la construction rassemble 587�898�entreprises. Elles r�alisent un chiffre d�affaires de 405�milliards d�euros et d�gagent une valeur ajout�e�(VA) de 128�milliards d�euros. Fin�2024, 1,5�million de personnes occupent un emploi salari� dans la construction.'}, {'cle': 'services', 'alias': '', 'valeur': 'En�2023, les services principalement marchands non financiers comptent plus de 2,3�millions d�entreprises. Ces entreprises r�alisent un chiffre d�affaires de 995�milliards d�euros et d�gagent une valeur ajout�e�(VA) de 475�milliards d�euros. Fin�2024, 7,5�millions de personnes (y compris les int�rimaires) occupent un emploi salari� dans les services principalement marchands non financiers.'}, {'cle': 'transports', 'alias': '', 'valeur': 'En�2023, les transports et l�entreposage rassemblent 193�101�entreprises. Elles r�alisent un chiffre d�affaires de 267�milliards d�euros et d�gagent une valeur ajout�e�(VA) de 102�milliards d�euros. Fin�2024, 1,5�million de personnes occupent un emploi salari� dans les transports et l�entreposage.'}, {'cle': 'entreprises de l��conomie sociale ', 'alias': '', 'valeur': "Les entreprises de l��conomie sociale se caract�risent par leur famille de l'�conomie sociale, � la fois priv� et � caract�re essentiellement non lucratif. En�2022, elles repr�sentent 9,8�% de l�emploi salari� total en �quivalent temps plein. Les associations emploient 73�% de ce volume de travail salari�; 14�% est employ� par les coop�ratives, 6�% par les mutuelles, 5�% par les fondations et 3�% par les autres organismes priv�s � but non-lucratif."}, {'cle': 'Population quartiers prioritaires de la politique de la ville  ', 'alias': 'QPV', 'valeur': 'Les quartiers prioritaires de la politique de la ville�(QPV) tels que d�finis par le d�cret n� 2015-1138 du 14 septembre 2015 regroupent 7,9�% de la population en 2020. '}, {'cle': 'Population unit�s urbaines ', 'alias': '', 'valeur': 'Les unit�s urbaines rassemblent toujours plus d�habitants. En�2022, en France m�tropolitaine, elles repr�sentent 78,8�% de la population, soit 51,9�millions d�habitants. � l�exception de l�unit� urbaine de Paris qui concentre pr�s de 11�millions d�habitants, les 10�plus grandes unit�s urbaines fran�aises comptent chacune entre 0,5�et 2�millions d�habitants. '}, {'cle': 'mode d�placement domicile travail', 'alias': '', 'valeur': 'Pour se rendre au travail, les personnes en emploi se d�placent majoritairement en voiture ou en deux-roues motoris�s (71�% en�2022). 15�% des personnes en emploi empruntent les transports en commun '}, {'cle': "d�pense nationale protection de l'environnement ", 'alias': '', 'valeur': "En�2022, la d�pense nationale en faveur de la protection de l'environnement s'�l�ve � 63,7�milliards d'euros�(Md�). Elle est d�di�e � la protection de l'air, de la biodiversit� et des paysages, la collecte et traitement des d�chets, la protection et d�pollution des sols et des eaux, la lutte contre le bruit et d'autres activit�s de protection de l'environnement (frais de fonctionnement de l'administration publique et des op�rateurs charg�s des questions environnementales notamment). Les entreprises sont les principaux financeurs des d�penses de protection de l'environnement (22,6�Md�, soit 35�%), devant les administrations publiques ���tat et ses minist�res, collectivit�s locales, organismes publics (22,2�Md�, soit 35�%) et les m�nages (18,1�Md�, soit 28�%). "}]