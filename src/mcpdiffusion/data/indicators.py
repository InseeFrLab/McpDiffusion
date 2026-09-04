"""Curated INSEE key indicators (homepage data)."""

# Fixme: I am wondering whether this really belongs in the source code or in a separate file or database
# Fixme: The 1st entry seems like a header (contains no real data), is that normal?
# Fixme: This seems like hardcoded, stale statistics... I don't know if this is normal
DICT_KV = [
    {"cle": "clé", "alias": "alias", "valeur": "valeur"},
    {
        "cle": "estimation de population France",
        "alias": "",
        "valeur": "Au 1er janvier 2026, la population résidant en France est estimée à 69,1 millions d'habitants.",
    },
    {
        "cle": "population légale France",
        "alias": "",
        "valeur": "Au 1er janvier 2023, la population de la France hors Mayotte s'établit officiellement à 68 094 000 habitants.",
    },
    {
        "cle": "immigrés France",
        "alias": "",
        "valeur": "En 2025, 8,0 millions d'immigrés vivent en France, soit 11,6 % de la population totale.",
    },
    {
        "cle": "population étrangère France",
        "alias": "",
        "valeur": "En 2025, la population étrangère vivant en France s'élève à 6,3 millions de personnes, soit 9,1 % de la population totale.",
    },
    {
        "cle": "naissances France",
        "alias": "",
        "valeur": "En 2025, le nombre de naissances en France est estimé à 645 000, soit une baisse de -2,1 % par rapport à 2024.",
    },
    {
        "cle": "indicateur conjoncturel de fécondité",
        "alias": "",
        "valeur": "En 2025, l'indicateur conjoncturel de fécondité (ICF) continue de diminuer. Il s'établit à 1,56 enfant par femme (1,53 en France métropolitaine), après 1,61 en 2024 (1,58 en France métropolitaine).",
    },
    {
        "cle": "décès France",
        "alias": "",
        "valeur": "En 2025, le nombre de décès en France est estimé à 651 000, en hausse de 1,5 % par rapport à 2024, après +0,3 % entre 2023 et 2024 (en tenant compte du fait que 2024 est une année bissextile).",
    },
    {
        "cle": "espérance de vie France",
        "alias": "",
        "valeur": "En 2025, l'espérance de vie à la naissance s'élève à 85,9 ans pour les femmes et à 80,3 ans pour les hommes. Elle augmente en 2025, de +0,1 an pour les femmes comme pour les hommes, pour atteindre un niveau historiquement élevé.",
    },
    {
        "cle": "mariages France",
        "alias": "",
        "valeur": "En 2025, le nombre de mariages célébrés en France est estimé à 251 000, dont 244 000 entre personnes de sexe différent et 7 000 entre personnes de même sexe. Le nombre de mariages augmente de 1,4 % par rapport à 2024, après +2,7 % entre 2023 et 2024 (en tenant compte du fait que 2024 est une année bissextile), alors que la tendance était plutôt à la baisse avant la crise sanitaire.",
    },
    {
        "cle": "ménages France",
        "alias": "",
        "valeur": "En 2023, la France hors Mayotte compte 31,3 millions de ménages.",
    },
    {
        "cle": "divorces France",
        "alias": "",
        "valeur": "128 043 divorces en 2016. Note : jusqu'en 2016, les divorces étaient des décisions de justice prononcées par un juge ; depuis 2017, les divorces par consentement mutuel passent par un acte notarié et ne sont plus comptabilisés de la même façon.",
    },
    {
        "cle": "inflation",
        "alias": "Indice des prix à la consommation – IPC ",
        "valeur": "En juin 2026, les prix à la consommation (IPC) augmentent de 1,8 % sur un an. Sur un mois, l'indice des prix à la consommation diminue de 0,3 %.",
    },
    {
        "cle": "Chômage BIT ",
        "alias": "",
        "valeur": "Au premier trimestre 2026, le taux de chômage  en France (hors Mayotte) augmente de 0,2 point et atteint 8,1 % . Le nombre de chômeurs est de  2,6 millions de personnes.",
    },
    {
        "cle": "emploi BIT",
        "alias": "",
        "valeur": "En moyenne sur l'année 2025, parmi les personnes âgées de 15 à 64 ans vivant en France, 69,3 % sont en emploi au sens du Bureau international du travail (BIT).",
    },
    {
        "cle": "PIB trimestriel",
        "alias": "croissance trimestrielle",
        "valeur": "Au premier trimestre 2026, le produit intérieur brut (PIB) en volume se replie légèrement (-0,1 %).",
    },
    {
        "cle": "PIB annuel",
        "alias": "croissance annuelle",
        "valeur": "En 2025, le PIB croît de 0,8 % en volume aux prix de l'année précédente.",
    },
    {
        "cle": "Dépenses de consommation des ménages en biens",
        "alias": "",
        "valeur": "En mai 2026, les dépenses de consommation des ménages en biens rebondissent sur un mois (+0,5 % en volume après -0,5 % en avril). Les volumes sont mesurés aux prix de l'année précédente chaînés (en milliards d'euros 2020) et corrigés des variations saisonnières et des effets des jours ouvrables (CVS-CJO).",
    },
    {
        "cle": "Climat des affaires",
        "alias": "",
        "valeur": "En juin 2026, l'indicateur synthétique du climat des affaires, calculé à partir des réponses des chefs d'entreprise des principaux secteurs d'activité marchands rebondit très légèrement, à 94, en deçà de son niveau moyen.",
    },
    {
        "cle": "climat de l'emploi",
        "alias": "",
        "valeur": "En juin 2026, l'indicateur du climat de l'emploi perd de nouveau trois points (après arrondi) et s'établit à 89, son niveau le plus bas depuis juin 2013 (hors crise sanitaire).",
    },
    {
        "cle": "production manufacturière",
        "alias": "Indice de la production industrielle - IPI",
        "valeur": "En mai 2026, après deux mois de hausse, la production se replie nettement dans l'industrie manufacturière (-1,0 % après +0,6 % en avril 2026). Dans l'ensemble de l'industrie, elle se replie aussi mais plus légèrement (-0,1 % après +0,3 %).",
    },
    {
        "cle": "niveau de vie",
        "alias": "",
        "valeur": "En 2024, en France métropolitaine, le niveau de vie médian de la population s'élève à 26 740 euros annuels. Il correspond à un revenu disponible de 2 228 euros par mois pour une personne seule.",
    },
    {
        "cle": "pouvoir d'achat",
        "alias": "",
        "valeur": "En 2025, le pouvoir d'achat du revenu disponible (RDB) des ménages se replie de 0,4 % après une hausse de 2,7 % en 2024. Ramené au niveau individuel et en tenant compte de l'évolution de la taille des ménages, le pouvoir d'achat baisse de 0,7 % après une hausse de 2,2 % en 2024",
    },
    {
        "cle": "balance commerciale",
        "alias": "",
        "valeur": "En 2025, les exportations en volume restent soutenues (+2,3 % après +3,2 % en 2024), tandis que les importations se redressent nettement (+2,8 % après -0,6 %). De ce fait, les échanges extérieurs pèsent sur la croissance de l'activité en 2025, à hauteur de -0,2 point de PIB, après l'avoir fortement soutenue en 2023 et 2024. ",
    },
    {
        "cle": "pauvreté monétaire",
        "alias": "",
        "valeur": "En 2024, 9,8 millions de personnes vivent avec un niveau de vie inférieur au seuil de pauvreté monétaire, soit 15,4 % de la population vivant dans un logement ordinaire en France métropolitaine.",
    },
    {
        "cle": "patrimoine",
        "alias": "",
        "valeur": "Début 2024, la moitié des ménages vivant en France déclarent un patrimoine brut supérieur à 205 100 euros. La moitié la mieux dotée en patrimoine brut possède collectivement 93 % de la masse totale de patrimoine. ",
    },
    {
        "cle": "état santé",
        "alias": "",
        "valeur": "En 2024, deux tiers des personnes âgées de 16 ans ou plus se déclarent en bonne ou très bonne santé. À l'opposé, près de 10 % jugent leur état de santé mauvais voire très mauvais.",
    },
    {
        "cle": "prestation handicap",
        "alias": "",
        "valeur": "Selon leur âge et leur situation, les personnes en situation de handicap ou de perte d'autonomie peuvent prétendre à différentes prestations. Fin 2023, 44 000 personnes ont un droit ouvert à l'allocation compensatrice pour tierce personne (ACTP) et 407 000 à la prestation de compensation du handicap (PCH). Par ailleurs, 1,4 million de personnes de 60 ans ou plus ont perçu l'allocation personnalisée d'autonomie (APA) au titre du mois de décembre 2023.",
    },
    {
        "cle": "dépenses liées à la culture",
        "alias": "",
        "valeur": "En 2025, les dépenses liées à la culture, au sport et aux loisirs s'élèvent à 108 milliards d'euros. Les services récréatifs, sportifs et culturels rassemblent 45 % de ces dépenses.",
    },
    {
        "cle": "Parc de logements",
        "alias": "",
        "valeur": "Au 1er janvier 2025, la France hors Mayotte compte 38,4 millions de logements. 82,5 % des logements sont des résidences principales et 54,4 % des logements individuels (maisons).",
    },
    {
        "cle": "logements vacants",
        "alias": "",
        "valeur": "Après avoir fortement augmenté entre 2005 et 2019, la part des logements vacants diminue, passant de 8,1 % en 2019 à 7,7 % en 2025 ; en 2025, 3,0 millions de logements sont vacants.",
    },
    {
        "cle": "résidences secondaires ou logements occasionnels",
        "alias": "",
        "valeur": "Au 1er janvier 2025, 3,8 millions de logements sont des résidences secondaires ou des logements occasionnels ; après avoir augmenté entre 2011 et 2017, leur part dans l'ensemble du parc est stable.",
    },
    {
        "cle": "ménages sont propriétaires de leur résidence principale",
        "alias": "",
        "valeur": "Au 1er janvier 2025, 57,4 % des ménages sont propriétaires de leur résidence principale.",
    },
    {
        "cle": "smic",
        "alias": "Salaire minimum interprofessionnel de croissance",
        "valeur": "Depuis le 1er janvier 2026, le Smic brut s'élève à 12,02 euros par heure, soit 1 823,03 euros par mois pour 151,67 heures de travail.",
    },
    {
        "cle": "salaire mensuel moyen en équivalent temps plein (EQTP) secteur privé",
        "alias": "",
        "valeur": "En 2023, le salaire mensuel moyen en équivalent temps plein (EQTP) dans le secteur privé est de 2 730 euros, nets de cotisations et contributions sociales.",
    },
    {
        "cle": "salaire mensuel moyen en équivalent temps plein (EQTP) secteur public",
        "alias": "",
        "valeur": "Dans la fonction publique, tous statuts confondus, un salarié gagne en moyenne 2 650 euros nets par mois en EQTP en 2023.",
    },
    {
        "cle": "revenus non salariés",
        "alias": "",
        "valeur": "En 2023, hors agriculture, les non-salariés classiques (micro-entrepreneurs exclus) retirent en moyenne 4 040 euros par mois de leur activité non salariée. Cette moyenne recouvre de fortes disparités selon la nature des emplois.",
    },
    {
        "cle": "salaires horaires",
        "alias": "",
        "valeur": "Au premier trimestre 2026, les salaires horaires augmentent de 0,3 % sur le trimestre et de 2,0 % sur un an",
    },
    {
        "cle": "coût horaire du travail",
        "alias": "Indice du coût du travail – ICT",
        "valeur": "Au premier trimestre 2026, le coût horaire du travail (salaires, cotisations et taxes, déduction faite des exonérations et subventions) de l'ensemble du secteur marchand non agricole (hors services aux ménages) freine significativement, dans le sillage des salaires : +0,5 % sur le trimestre et + 2,3 % sur un an.",
    },
    {
        "cle": "création entreprises",
        "alias": "",
        "valeur": "En 2025, 1 165 800 entreprises ont été créées en France, dont 758 500 sous forme d'entrepreneurs individuels ayant adopté le régime de la microentreprise (micro-entrepreneurs).",
    },
    {
        "cle": "défaillances d'entreprises",
        "alias": "",
        "valeur": "En 2025, 68 872 unités légales ont été en situation de défaillance.",
    },
    {
        "cle": "entreprises marchandes non agricoles et non financières en France",
        "alias": "",
        "valeur": "En 2023, en France, les secteurs marchands non agricoles et non financiers (incluant toutefois les exploitations forestières, les auxiliaires de services financiers et d'assurance et les holdings) comptent 5,2 millions d'entreprises. Ces entreprises emploient 15,9 millions de salariés en équivalent temps plein (EQTP).",
    },
    {
        "cle": "exploitations agricoles",
        "alias": "",
        "valeur": "Dans le secteur agricole, l'usage est de compter plutôt des exploitations agricoles ; en 2023, la France métropolitaine en compte 349 600 et la main d'œuvre agricole s'élève à 663 200 EQTP.",
    },
    {
        "cle": "commerce",
        "alias": "",
        "valeur": "En 2023, le commerce rassemble 739 128 entreprises. Elles réalisent un chiffre d'affaires de 1 728 milliards d'euros et dégagent une valeur ajoutée (VA) de 272 milliards d'euros. Fin 2024, 3,4 millions de personnes occupent un emploi salarié dans le commerce.",
    },
    {
        "cle": "industrie",
        "alias": "",
        "valeur": "En 2023, l'industrie rassemble 322 386 entreprises. Elles réalisent un chiffre d'affaire de 1 544 milliards d'euros et dégagent une valeur ajoutée (VA) de 368 milliards d'euros. Fin 2024, 3,3 millions de personnes occupent un emploi salarié dans l'industrie.",
    },
    {
        "cle": "construction",
        "alias": "",
        "valeur": "En 2023, la construction rassemble 587 898 entreprises. Elles réalisent un chiffre d'affaires de 405 milliards d'euros et dégagent une valeur ajoutée (VA) de 128 milliards d'euros. Fin 2024, 1,5 million de personnes occupent un emploi salarié dans la construction.",
    },
    {
        "cle": "services",
        "alias": "",
        "valeur": "En 2023, les services principalement marchands non financiers comptent plus de 2,3 millions d'entreprises. Ces entreprises réalisent un chiffre d'affaires de 995 milliards d'euros et dégagent une valeur ajoutée (VA) de 475 milliards d'euros. Fin 2024, 7,5 millions de personnes (y compris les intérimaires) occupent un emploi salarié dans les services principalement marchands non financiers.",
    },
    {
        "cle": "transports",
        "alias": "",
        "valeur": "En 2023, les transports et l'entreposage rassemblent 193 101 entreprises. Elles réalisent un chiffre d'affaires de 267 milliards d'euros et dégagent une valeur ajoutée (VA) de 102 milliards d'euros. Fin 2024, 1,5 million de personnes occupent un emploi salarié dans les transports et l'entreposage.",
    },
    {
        "cle": "entreprises de l'économie sociale",
        "alias": "",
        "valeur": "Les entreprises de l'économie sociale se caractérisent par leur famille de l'économie sociale, à la fois privé et à caractère essentiellement non lucratif. En 2022, elles représentent 9,8 % de l'emploi salarié total en équivalent temps plein. Les associations emploient 73 % de ce volume de travail salarié ; 14 % est employé par les coopératives, 6 % par les mutuelles, 5 % par les fondations et 3 % par les autres organismes privés à but non-lucratif.",
    },
    {
        "cle": "Population quartiers prioritaires de la politique de la ville",
        "alias": "QPV",
        "valeur": "Les quartiers prioritaires de la politique de la ville (QPV) tels que définis par le décret n° 2015-1138 du 14 septembre 2015 regroupent 7,9 % de la population en 2020.",
    },
    {
        "cle": "Population unités urbaines",
        "alias": "",
        "valeur": "Les unités urbaines rassemblent toujours plus d'habitants. En 2022, en France métropolitaine, elles représentent 78,8 % de la population, soit 51,9 millions d'habitants. À l'exception de l'unité urbaine de Paris qui concentre près de 11 millions d'habitants, les 10 plus grandes unités urbaines françaises comptent chacune entre 0,5 et 2 millions d'habitants.",
    },
    {
        "cle": "mode déplacement domicile travail",
        "alias": "",
        "valeur": "Pour se rendre au travail, les personnes en emploi se déplacent majoritairement en voiture ou en deux-roues motorisés (71 % en 2022). 15 % des personnes en emploi empruntent les transports en commun.",
    },
    {
        "cle": "dépense nationale protection de l'environnement",
        "alias": "",
        "valeur": "En 2022, la dépense nationale en faveur de la protection de l'environnement s'élève à 63,7 milliards d'euros (Md€). Elle est dédiée à la protection de l'air, de la biodiversité et des paysages, la collecte et traitement des déchets, la protection et dépollution des sols et des eaux, la lutte contre le bruit et d'autres activités de protection de l'environnement (frais de fonctionnement de l'administration publique et des opérateurs chargés des questions environnementales notamment). Les entreprises sont les principaux financeurs des dépenses de protection de l'environnement (22,6 Md€, soit 35 %), devant les administrations publiques (État et ses ministères, collectivités locales, organismes publics) (22,2 Md€, soit 35 %) et les ménages (18,1 Md€, soit 28 %).",
    },
    {
        "cle": "indice de référence des loyers",
        "alias": "IRL",
        "valeur": "Au deuxième trimestre 2026, l'indice de référence des loyers s'établit à 148,37. Sur un an, il augmente de 1,15 % après +0,78 % au trimestre précédent.",
    },
    {
        "cle": "indice des loyers commerciaux",
        "alias": "ILC",
        "valeur": "Au premier trimestre 2026, l'indice des loyers commerciaux s'établit à 135,26. Sur un an, il baisse de 0,45 % (après -0,50 % au trimestre précédent).",
    },
    {
        "cle": "indice des loyers des activités tertiaires",
        "alias": "ILAT",
        "valeur": "Au premier trimestre 2026, l'indice des loyers des activités tertiaires s'établit à 137,42. Sur un an, il augmente de 0,09 % (après -0,06 % au trimestre précédent).",
    },
    {
        "cle": "indice du coût de la construction",
        "alias": "ICC",
        "valeur": "L'indice du coût de la construction (ICC) s'établit à 2 084 au premier trimestre 2026. Il est en hausse de 1,26 % sur un trimestre (après +0,10 % au trimestre précédent). Sur un an, il baisse de 2,89 % (après -2,37 % au trimestre précédent).",
    },
    {
        "cle": "index du bâtiment tous corps d'état",
        "alias": "BT01 ; index bâtiment BT01",
        "valeur": "En mai 2026, l'index Bâtiment BT01 « Tous corps d'état » s'établit à 137,9, en référence 100 en 2010.",
    },
    {
        "cle": "index général des travaux publics",
        "alias": "TP01 ; index travaux publics TP01",
        "valeur": "En mai 2026, l'index Travaux publics TP01 « Index général tous travaux » s'établit à 140,4, en référence 100 en 2010.",
    },
    {
        "cle": "index ingénierie",
        "alias": "ING ; indice ING",
        "valeur": "En mai 2026, l'index divers de la construction ING « Ingénierie » s'établit à 138,3, en référence 100 en 2010.",
    },
]
