from fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from tools import register_tools

import uvicorn
from starlette.middleware.trustedhost import TrustedHostMiddleware #remove before flight

import os
import sys
from pathlib import Path



#logs
import logging
from helpers.logging import MAIN_LOGGER_NAME, UVICORN_LOGGING_CONFIG
logger = logging.getLogger(MAIN_LOGGER_NAME)


# env
from dotenv import load_dotenv
load_dotenv()

# Initialize FastMCP server ---
transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False)


mcp = FastMCP(
    "mcp-INSEE"
    )

# ---

# add tools ---

register_tools(mcp)

# ---

app = mcp.http_app()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"]) # add to test, remove before flight

if __name__ == "__main__":
    port_str = os.getenv("MCP_PORT", "8000")
    host_str = os.getenv("MCP_HOST", "0.0.0.0") # Set MCP_HOST=127.0.0.1 for local development to follow MCP security best practices
    try:
        port = int(port_str)
    except ValueError:
        print(
            f"Error: Invalid MCP_PORT environment variable: {port_str}",
            file=sys.stderr,
        )
        sys.exit(1)
    uvicorn.run(app, host=host_str, port=port,
                proxy_headers=True,forwarded_allow_ips="*", #to avoid issues with dns rebinding
                log_level="info",
                log_config=UVICORN_LOGGING_CONFIG)