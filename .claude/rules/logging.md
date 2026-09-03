# Logging

Two channels, two audiences. Confusing them is the common mistake.

- **Client logging** — `ctx.debug/info/warning/error()`. Travels to the MCP client over the protocol.
  Audience: the calling LLM and the person watching it.
- **Server logging** — Python `logging`. Goes to stdout and the aggregator. Audience: whoever is on call.

Never send the same message to both.

## Client logging

- Use it to narrate a call so the model can react: which index was searched, why a result set came back
  empty, which filter was ignored.
- Never use it to report failure. `ctx.error()` does not fail the call — raise a `ToolError` instead.
- Never send credentials, connection strings or upstream response bodies. This leaves the process.
- It is async: await it. Each call is a protocol notification, so never put one inside a loop over results.
- Structured data goes in `extra=`, not formatted into the message.
- It needs a `Context`, so it exists only during a request.

## Use the middleware

- Never reimplement what the middleware provides: `LoggingMiddleware` (human-readable),
  `StructuredLoggingMiddleware` (JSON for aggregation), `TimingMiddleware` and `DetailedTimingMiddleware`
  (durations), `ErrorHandlingMiddleware` (exceptions). A per-tool decorator that logs entry, duration and
  errors is one of these.
- `LoggingMiddleware(include_payloads=...)` truncates, it does not redact. Leave it `False` unless a custom
  `logger` with a redacting filter is in place.
- Register logging middleware last, so it records execution after the rest of the chain has run.

## Who logs what

- **Middleware logs failures, not services.** `ErrorHandlingMiddleware` already catches, logs and converts
  every exception. Code that logs before raising records the same failure twice.
- A service logs only what the exception cannot carry, and never at `error` level.
- Never log credentials, tokens or request bodies.

## Configuration

- Configure logging once at startup, never at import time. `logging.basicConfig` in a module body fires as
  a side effect of importing that module and cannot be overridden by the process hosting the app.
- The configuration must apply whether the server runs via `__main__` or under an external ASGI server.
- Logger names follow the module: `logging.getLogger(__name__)`. Never a hand-picked shared name.

## Where the channels meet

Everything sent with `ctx.log()` is also written to the server log at `DEBUG` on the
`fastmcp.server.context.to_client` logger. Enable it to audit what clients were told — do not log the same
message twice yourself.

## Protocol notes

- Log messages are one-way notifications, so they always reach the client. (Two-way features like sampling
  were removed from the protocol; logging was not.)
- Ignore the SDK's `MCPDeprecationWarning` about the logging capability. It is about the handshake, not the
  messages. They still arrive.
- The client decides which levels it keeps. `logging/setLevel` no longer works, so never rely on the server
  filtering levels for a client.
