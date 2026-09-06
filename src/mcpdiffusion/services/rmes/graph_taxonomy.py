"""Sorting RMES graphs into the families declared in `data/rmes/graph_categories.py`.

Pure: no client, no I/O, and no state worth a class -- the graph base is passed in rather than
read from a module global, so these functions work against any store.

The static table says *which* families exist; this module says what matching one means.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ...data.rmes.graph_categories import CATEGORY_DEFINITIONS, FALLBACK_CATEGORY_DEFINITION
from ...models.rmes import CategoryBucket, GraphRow

MAX_EXAMPLES_PER_CATEGORY = 5


# ----------------------------------------------------------------------------------------------------------------------
# Rules ----------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# A matcher decides whether a graph path belongs to a family.
CategoryMatcher = Callable[[str], bool]


@dataclass(frozen=True)
class CategoryRule:
    """One family, with the test that decides whether a graph path belongs to it."""

    key: str
    label: str
    description: str
    match: CategoryMatcher


def build_matcher(definition: dict) -> CategoryMatcher:
    """Turn a family's declared test into a callable.

    A definition with neither test matches everything, which is how the fallback works.
    """
    prefixes = tuple(definition.get("prefixes", ()))
    paths = frozenset(definition.get("paths", ()))
    if not prefixes and not paths:
        return lambda path: True
    return lambda path: path.startswith(prefixes) if prefixes else path in paths


def build_rule(definition: dict) -> CategoryRule:
    """Pair a family's text with its matcher."""
    return CategoryRule(
        key=definition["key"],
        label=definition["label"],
        description=definition["description"],
        match=build_matcher(definition),
    )


CATEGORY_RULES: list[CategoryRule] = [build_rule(entry) for entry in CATEGORY_DEFINITIONS]
FALLBACK_RULE: CategoryRule = build_rule(FALLBACK_CATEGORY_DEFINITION)
ALL_RULES: list[CategoryRule] = [*CATEGORY_RULES, FALLBACK_RULE]


# ----------------------------------------------------------------------------------------------------------------------
# Classification -------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def strip_graph_base_uri(graph_uri: str, graph_base_uri: str) -> str:
    """Return the path part of a graph URI, which is what the rules match on.

    A URI from another store keeps its full form, so it matches no rule and lands in the fallback.
    """
    if graph_uri.startswith(graph_base_uri):
        return graph_uri[len(graph_base_uri) :]
    return graph_uri


def categorize_graph(graph_uri: str, graph_base_uri: str) -> CategoryRule:
    """Return the first family whose rule matches the graph, or the fallback."""
    path = strip_graph_base_uri(graph_uri, graph_base_uri)
    for rule in CATEGORY_RULES:
        if rule.match(path):
            return rule
    return FALLBACK_RULE


# ----------------------------------------------------------------------------------------------------------------------
# Filtering and grouping -----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def filter_graph_rows(
    rows: list[GraphRow],
    graph_uri_substring: str | None,
    graph_category: str | None,
    graph_base_uri: str,
) -> list[GraphRow]:
    """Narrow the graph list by URI substring and by family. Both filters are optional."""
    if graph_uri_substring:
        needle = graph_uri_substring.lower()
        rows = [row for row in rows if needle in row.graph.lower()]
    if graph_category:
        rows = [row for row in rows if categorize_graph(row.graph, graph_base_uri).key == graph_category]
    return rows


def build_category_summary(
    rows: list[GraphRow],
    include_graphs: bool,
    graph_base_uri: str,
) -> list[CategoryBucket]:
    """Group the graphs by family, in rule order, dropping families that matched nothing.

    Each row is categorised once: `include_graphs` only decides whether the grouped rows are
    reported alongside the counts.
    """
    rows_by_category: dict[str, list[GraphRow]] = {}
    for row in rows:
        rows_by_category.setdefault(categorize_graph(row.graph, graph_base_uri).key, []).append(row)

    summary: list[CategoryBucket] = []
    for rule in ALL_RULES:
        category_rows = rows_by_category.get(rule.key)
        if not category_rows:
            continue
        summary.append(
            CategoryBucket(
                category=rule.key,
                label=rule.label,
                description=rule.description,
                count=len(category_rows),
                total_triples=sum(row.triples for row in category_rows),
                examples=[row.graph for row in category_rows[:MAX_EXAMPLES_PER_CATEGORY]],
                graphs=(sorted(category_rows, key=lambda row: row.triples, reverse=True) if include_graphs else None),
            )
        )
    return summary
