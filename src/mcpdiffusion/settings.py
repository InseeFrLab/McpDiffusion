"""Every value this server can be configured with."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # HTTP server ------------------------------------------------------------------------------------------------------
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    # JSON list. "*" accepts any host and is unsafe once the server is publicly reachable.
    allowed_hosts: list[str] = ["*"]
    # Peers whose X-Forwarded-For header is believed; anything else keeps its real socket address.
    # Accepts addresses, CIDR networks and literals. Widening this lets callers forge their own address.
    trusted_proxy_hosts: list[str] = ["127.0.0.1"]

    # Tool selection ---------------------------------------------------------------------------------------------------
    enable_inseefr_tools: bool = True
    enable_melodi_tools: bool = True
    enable_rmes_tools: bool = True

    # Elasticsearch ----------------------------------------------------------------------------------------------------
    es_host: str
    es_index_publications: str = "produit"
    es_index_melodi_datasets: str = "melodi_datasets"
    es_index_melodi_columns: str = "melodi_columns"
    # Elasticsearch is often internal with a self-signed certificate.
    es_tls_verify: bool = True
    es_request_timeout_seconds: int = 30

    # INSEE services ---------------------------------------------------------------------------------------------------
    insee_base_url: str = "https://www.insee.fr"
    insee_request_timeout_seconds: int = 30
    insee_connect_timeout_seconds: int = 10
    melodi_data_base_url: str = "https://api.insee.fr/melodi/data"
    melodi_request_timeout_seconds: int = 30
    melodi_connect_timeout_seconds: int = 10
    # RMES takes its timeout per query, from the tool's own input.
    rmes_endpoint: str = "https://rdf.insee.fr/sparql"

    # Rate limiting ----------------------------------------------------------------------------------------------------
    rate_limit_max_requests: int = 100
    rate_limit_window_minutes: int = 1

    # Logging ----------------------------------------------------------------------------------------------------------
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


def load_settings() -> Settings:
    return Settings()
