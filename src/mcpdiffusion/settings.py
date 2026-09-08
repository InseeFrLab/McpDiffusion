"""Every value this server can be configured with."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # HTTP server ------------------------------------------------------------------------------------------------------
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    # JSON list of the hostnames clients use to reach this server, checked against the Host
    # header. "*" accepts any host, which disables the check.
    allowed_hosts: list[str] = ["*"]
    # JSON list of browser origins allowed to call the server. Empty rejects every cross-origin
    # browser request, which is right until a browser-based client needs in.
    allowed_origins: list[str] = []
    # Peers whose X-Forwarded-For header is believed; anything else keeps its real socket address.
    # Accepts addresses, CIDR networks and literals. Widening this lets callers forge their own address.
    trusted_proxy_hosts: list[str] = ["127.0.0.1"]

    # Tool selection ---------------------------------------------------------------------------------------------------
    enable_inseefr_tools: bool = True
    enable_melodi_tools: bool = True
    enable_rmes_tools: bool = True
    # Reporting only: it records to the server log and needs no backend.
    enable_feedback_tool: bool = True

    # Elasticsearch ----------------------------------------------------------------------------------------------------
    # Only the insee.fr and Melodi tools search Elasticsearch; rmes runs without it, so the
    # host is genuinely absent rather than empty when they are disabled.
    es_host: str | None = None
    es_index_publications: str = "produit"
    es_index_melodi_datasets: str = "melodi_datasets"
    es_index_melodi_columns: str = "melodi_columns"
    # Elasticsearch is often internal with a self-signed certificate.
    es_tls_verify: bool = True
    es_request_timeout_seconds: int = 30
    # Retries the client makes itself before a search fails. Raising it hides brief outages;
    # lowering it surfaces them sooner.
    es_max_retries: int = 2

    # INSEE services ---------------------------------------------------------------------------------------------------
    insee_base_url: str = "https://www.insee.fr"
    insee_request_timeout_seconds: int = 30
    insee_connect_timeout_seconds: int = 10
    # A rendered publication is truncated past this many characters, so one document cannot
    # fill the calling model's context. Tune it to the context budget of the client in use.
    insee_document_max_markdown_chars: int = 30_000
    melodi_data_base_url: str = "https://api.insee.fr/melodi/data"
    melodi_request_timeout_seconds: int = 30
    melodi_connect_timeout_seconds: int = 10
    # Where queries are POSTed. RMES takes its timeout per query, from the tool's own input.
    rmes_sparql_endpoint_url: str = "https://rdf.insee.fr/sparql"
    # Not an address to call: the namespace every named graph URI starts with, stripped off
    # before a graph is matched against a family.
    rmes_graph_base_uri: str = "http://rdf.insee.fr/graphes/"
    # Listing every graph counts triples across the whole store, so it gets its own budget.
    rmes_graph_listing_timeout_seconds: float = 45.0
    rmes_graph_listing_max_rows: int = 1000
    rmes_graph_cache_ttl_seconds: float = 3600.0

    # Rate limiting ----------------------------------------------------------------------------------------------------
    rate_limit_max_requests: int = 100
    rate_limit_window_minutes: int = 1

    # Logging ----------------------------------------------------------------------------------------------------------
    log_level: str = "INFO"

    @model_validator(mode="after")
    def require_elasticsearch_when_it_is_searched(self) -> "Settings":
        """Fail at startup rather than on the first search that needs a host."""
        if self.es_host is None and (self.enable_inseefr_tools or self.enable_melodi_tools):
            raise ValueError(
                "ES_HOST is required because the insee.fr or Melodi tools are enabled. "
                "Set it, or disable those families with ENABLE_INSEEFR_TOOLS=false and "
                "ENABLE_MELODI_TOOLS=false."
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


def load_settings() -> Settings:
    return Settings()
