"""Centralized application settings validated at import time via Pydantic."""

from functools import lru_cache
# Fixme: prefer more recent syntax - ex: str | None instead of Optional
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Elasticsearch
    # Fixme: if the environment variable name matches the variable name, there is no need for an alias
    es_host: Optional[str] = Field(default=None, alias="ES_HOST")
    es_index_produits: str = Field(default="produit", alias="ES_INDEX_PRODUITS")
    es_index_melodi_datasets: str = Field(
        default="melodi_datasets", alias="ES_INDEX_MELODI_DATASETS"
    )
    es_index_melodi_columns: str = Field(
        default="melodi_columns", alias="ES_INDEX_MELODI_COLUMNS"
    )

    # TLS
    tls_verify: bool = Field(default=True, alias="TLS_VERIFY")

    # Server
    mcp_host: str = Field(default="0.0.0.0", alias="MCP_HOST")
    mcp_port: int = Field(default=8000, alias="MCP_PORT")
    allowed_hosts: str = Field(default="*", alias="ALLOWED_HOSTS")
    # Fixme: some variables are missing from the '.env.example' file
    forwarded_allow_ips: str = Field(default="*", alias="FORWARDED_ALLOW_IPS")

    # Rate limiting
    global_request_min: int = Field(default=100, alias="GLOBAL_REQUEST_MIN")
    tz: str = Field(default="Europe/Paris", alias="TZ")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Tool selection
    enable_melodi : bool = Field(default=True, alias = "ENABLE_MELODI")
    enable_inseefr : bool = Field(default=True, alias = "ENABLE_INSEEFR")
    enable_rmes : bool = Field(default=True, alias = "ENABLE_RMES")


    # RMES / SPARQL
    rmes_endpoint: str = Field(
        default="https://rdf.insee.fr/sparql", alias="RMES_ENDPOINT"
    )

    # Melodi
    melodi_data_base_url: str = Field(
        default="https://api.insee.fr/melodi/data", alias="MELODI_DATA_BASE_URL"
    )

    # INSEE.fr
    insee_base_url: str = Field(
        default="https://www.insee.fr", alias="INSEE_BASE_URL"
    )

    # Fixme: this is just a preference for reading but multiline objects reads better
    #   I also think 'populate_by_name' can be ignored if we get rid of aliases
    #   Eventually 'SettingsConfigDict' is better for config than a plain dict since it catches typo'd key
    #   Beware .env file resolves relative to the current working directory
    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}


@lru_cache
def get_settings() -> Settings:
    return Settings()
