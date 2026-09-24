"""What a tool can ask FastMCP to inject, one module per source.

A tool declares what it needs in its signature; FastMCP resolves it per request and hides the
parameter from the tool schema, so the LLM never sees it. Nothing is re-exported here: a tool
imports from its own source's module, so adding a source adds a file rather than editing one.
"""
