"""INSEE theme mappings and conjoncture sub-themes."""

# Fixme: Is that the right place for this kind of data? In the source code?
#  Maybe a JSON file or a database is a better place
# Fixme: This seems like mapping themes to IDs manually, this is fragile if so...
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


DICT_THEME_CONJ: dict[str, list[str]] = {
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
        "Indice du cout horaire du travail revise - Tous salaries (ICHT, ICHTrev-TS)"
        " - Publication arretee depuis le 06/10/2023",
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
