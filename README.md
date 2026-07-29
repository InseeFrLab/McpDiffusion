# mcp_diffusion

> Disclaimer : This project is in BETA. It should not be considered a finished nor an official product supported by INSEE.

MCP server project to use INSEE public data with your favorite models. Data include publications and reports, datasets and concept definitions.

- publications and reports are a subset of https://www.insee.fr/en/statistiques

- datsets : https://catalogue-donnees.insee.fr/en/catalogue/recherche

- concept definitions : https://www.insee.fr/en/metadonnees/definitions

The server rely on an ElasticSearch database which is not public at the moment. The only independent tool is the RMES search tool to retrieve concept definitions.

# To be translated

Ce serveur MCP combine 3 sources de données INSEE et agit comme un endpoint unique pour exposer les services de l'INSEE aux Large Language Models (LLMs).

## Les sources de données

- RMES : Ontologie de la sémantique INSEE et des méthodes statistiques (pas encore implem.)
- MELODI : API rest qui expose les jeux de données
- insee.fr : Site web http contenant les publications produites par l'organisme.   


## Dossiers

- helpers : config des logs et decorateur sur les tools

- tools : repertoire avec 1 tool par fichier. Le `init.py`permet d'en activer/désactiver

## Pour lancer

Après avoir copié le `.env.example` en `.env`. Lancer le serveur avec

```python3 server.py```

/!\ Sans l'instance d'elastic, il n'y a que les tools RMES d'exploitable.