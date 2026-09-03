# Git

Commits exist to produce a readable changelog. The existing history does not follow these rules —
do not imitate it.

## Committing

- Never commit or push unless asked.
- One concern per commit. If the subject needs "and", it is two commits.

## Message format

[Conventional Commits](https://www.conventionalcommits.org): `type(scope): subject`, with the scope
taxonomy below.

- Changelog types: `feat` (new capability), `fix` (something broken for a user now works).
- Silent types: `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`.
- Pick the type by what the line would say in release notes. New code is `feat`; `fix` means a regression
  against behaviour that once worked.
- Subject: imperative, lowercase, no trailing period. Say what the change gives a user, not which files moved.

### Scope

- User-facing changes take the data source: `insee`, `melodi`, `rmes`.
- Internal changes take the module area: `server`, `tools`, `services`, `config`, `core`, `docker`, `ci`.
- One scope per commit — where the capability lives, not every directory touched.
- Two data sources gaining independent capability is two commits.
- A cross-cutting change with no primary home takes no scope. Never comma-separate scopes.

## Branches and merging

- Branch off `main`. Never commit to `main` directly.
- Branches squash-merge. Branch commits may be WIP; the squash subject becomes the changelog line and
  describes the whole branch, not its final commit.

## Breaking changes

- Mark with `!` plus a `BREAKING CHANGE:` footer stating the migration:
  `feat(melodi)!: rename the dataset filter argument`.
- Breaking here means the **tool contract** changed: a renamed tool, a changed schema, a reordered workflow.
  Connected clients keep calling the old shape and fail silently. A description rewrite is not breaking.

## Versions

- Never edit `version` in `pyproject.toml` in a feature or fix commit.
- Versions and `CHANGELOG.md` are derived from commit history at release time, in a separate
  `chore(release):` commit. Do not hand-write either.
- CI builds and pushes an image on every push to `main` and on `v*` tags. A tag is a release action —
  never push one casually.
