# Python conventions

## Functions and side effects

Default to pure: same arguments in, same value out.

- Push I/O to the edges. Parsing, filtering, query building and result shaping stay pure.
- Never read a global inside a function — no `get_settings()`, no module-level client or cache.
- Never mutate an argument. Return a new value.
- No I/O and no clock reads at import time.
- Take what you need as a parameter, keyword-only unless it is the subject of the call. Pass specific
  values, never a whole configuration object.

## Typing and syntax

- Target Python 3.12.
- `str | None`, never `Optional[str]`. Never mix both styles.
- Annotate every return, including `-> None`. A function that always raises returns `NoReturn`.
- Alias a composed type you repeat: `TableOfContents = list[dict[str, str]]`.

## Async

- Async for anything doing I/O.
- Never call a blocking API inside a coroutine. If it cannot be avoided, tell me before writing it.

## Naming

Spell names out. The reader should not have to look up what something holds.

- `settings`, not `s`. `elasticsearch_client`, not `es`.
- Name what an argument is: `search_input`, not `params`.
- A name broader than the behaviour is misleading.
- Functions start with a verb that describes the actual work: `fail()` always raises, so `raise_tool_error()`.
- `get_` is for cheap in-memory lookups. Anything doing I/O is `fetch_`, `load_` or `search_`.

## Layout

- Dicts, lists and other objects: multiline, one entry per line, including as call arguments. The
  formatter collapses anything that fits on one line and never splits it for you — a **trailing comma
  on the last entry** is what keeps it exploded, so write one.
- Signatures and calls with two or more arguments: multiline, one per line, with the same trailing comma.
- Calls with more than two arguments name each one. Positional only where keywords are forbidden
  (`getattr`, `dict`, `join`).
- Imports at the top of the module, never inside a function.
- Text spanning more than one line is a triple-quoted string, `textwrap.dedent`-ed when indented.
- Never glue adjacent literals or chain `+`: implicit concatenation drops the space at line breaks.
- Long text is data. Keep it out of `if` branches and out of multi-source assembly.
