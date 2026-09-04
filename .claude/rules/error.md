# Error handling

Errors are part of the tool contract: the caller is an LLM, so an error must tell it what to do next.
A failed call returns the same result shape as a successful one, with `is_error` set. `is_error` is a flag,
not a code, and every documented client path reads the reason from `content[0].text`. The message is the
error contract — consistency means a consistent message, produced in one place.

## Where errors live

- `core/errors.py` owns every error type. Nothing else defines an error enum, model or vocabulary.
- Error types subclass `ToolError` — its message always reaches the client. Anything else is an internal
  fault and must not leak.
- Code and retryability are attributes on the exception, never formatted into the message.

## Raising

- Services raise. Tools do not build error messages.
- Raise the narrowest type that fits.
- Input validation belongs in the Pydantic model, not a runtime check in the tool.
- An empty result is not an error. Return an empty list and a count.

## Message content

Name the backend and operation that failed, the shortest useful excerpt of the upstream error, and the next
step — the offending parameter, or the tool that produces a valid value. Never a stack trace or a full body.

## Catching

- Catch the narrowest upstream exception you can name. Never `except Exception` or `except BaseException`
  (it swallows `CancelledError`).
- Translate once, at the boundary owning the dependency. Never re-wrap an already typed error.
- Never swallow: no empty `except`, no default on failure, no log-and-continue.
- Chain with `raise ... from exc`. Server-side hygiene only: `__cause__` never crosses the wire, so it
  leaks nothing, and Python keeps the original either way — this just states that it was the cause rather
  than an error raised while handling one.

## Use what FastMCP provides

- Set `mask_error_details=True` on the `FastMCP` instance. It defaults to `False`, which sends every raw
  exception message to the client. With it on, the call still fails visibly but unexpected exceptions carry a
  generic message; `ToolError` subclasses keep theirs.
- `ErrorHandlingMiddleware` catches, logs and converts every exception. Register it first, so it sees the
  rest of the chain. Failures are logged there, not by the code that raises — see `logging.md`.
- `RetryMiddleware` handles transient failures with backoff. Do not write a retry loop.
