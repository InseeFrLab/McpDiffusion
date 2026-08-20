"""Centralized application settings validated at import time via Pydantic."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Elasticsearch
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
    forwarded_allow_ips: str = Field(default="*", alias="FORWARDED_ALLOW_IPS")

    # Rate limiting
    global_request_min: int = Field(default=100, alias="GLOBAL_REQUEST_MIN")
    tz: str = Field(default="Europe/Paris", alias="TZ")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Tool selection
    toollist: Optional[str] = Field(default=None, alias="TOOLLIST")

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

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}


@lru_cache
def get_settings() -> Settings:
    return Settings()
