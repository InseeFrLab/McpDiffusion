"""Unit tests for mcpdiffusion.services.insee_search (pure logic, no ES)."""

from mcpdiffusion.services.insee_search import (
    _coerce_hit_value,
    apply_collection_filters,
    build_text_clauses,
)

# ===================================================================
# _coerce_hit_value
# ===================================================================


class TestCoerceHitValue:
    def test_none_returns_none(self):
        assert _coerce_hit_value(None) is None

    def test_string_passthrough(self):
        assert _coerce_hit_value("hello") == "hello"

    def test_integer_coerced_to_string(self):
        assert _coerce_hit_value(42) == "42"

    def test_list_joined(self):
        assert _coerce_hit_value(["a", "b", "c"]) == "a, b, c"

    def test_empty_list_returns_none(self):
        assert _coerce_hit_value([]) is None

    def test_single_element_list(self):
        assert _coerce_hit_value(["only"]) == "only"


# ===================================================================
# build_text_clauses
# ===================================================================


class TestBuildTextClauses:
    def test_no_arguments_returns_empty_lists(self):
        must, filters, should, must_not = build_text_clauses(None, None)
        assert must == []
        assert filters == []
        assert should == []
        assert must_not == []

    def test_query_adds_must_and_should(self):
        must, filters, should, must_not = build_text_clauses("population", None)
        assert len(must) == 1
        assert len(should) == 1

    def test_year_adds_filter(self):
        must, filters, should, must_not = build_text_clauses(None, 2024)
        assert must == []
        assert len(filters) == 1

    def test_query_and_year_combined(self):
        must, filters, should, must_not = build_text_clauses("PIB", 2023)
        assert len(must) == 1
        assert len(filters) == 1

    def test_keywords_add_should_clauses(self):
        must, filters, should, must_not = build_text_clauses(
            None,
            None,
            keywords=["eco", "stats"],
        )
        assert len(should) == 2

    def test_empty_keywords_ignored(self):
        must, filters, should, must_not = build_text_clauses(None, None, keywords=[])
        assert should == []

    def test_query_with_keywords(self):
        must, filters, should, must_not = build_text_clauses(
            "chomage",
            None,
            keywords=["emploi"],
        )
        assert len(must) == 1
        assert len(should) == 2  # match_phrase + keyword


# ===================================================================
# apply_collection_filters
# ===================================================================


class TestApplyCollectionFilters:
    def test_must_only_rapides(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=True,
        )
        assert len(filters) == 1

    def test_must_not_rapides(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=True,
            must_only_rapides=False,
        )
        assert len(filters) == 1

    def test_no_rapides_filter_when_both_false(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
        )
        assert filters == []
        assert should == []

    def test_chiffre_clef_adds_filter(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
            chiffre_clef=True,
        )
        assert len(filters) == 1

    def test_valid_theme_adds_filter(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
            theme="Demographie",
        )
        assert len(filters) == 1

    def test_theme_all_ignored(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
            theme="ALL",
        )
        assert filters == []

    def test_unknown_theme_ignored(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
            theme="NotATheme",
        )
        assert filters == []

    def test_valid_geo_niveau(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
            geo_niveau="COMMUNE",
        )
        assert len(filters) == 1

    def test_unknown_geo_niveau_ignored(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
            geo_niveau="MARS",
        )
        assert filters == []

    def test_geo_keyword_adds_two_should_clauses(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
            geo_keyword="Paris",
        )
        assert len(should) == 2

    def test_geo_keyword_all_ignored(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
            geo_keyword="all",
        )
        assert should == []

    def test_geo_keyword_all_case_insensitive(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=False,
            must_only_rapides=False,
            geo_keyword="ALL",
        )
        assert should == []

    def test_preserves_existing_filters(self):
        initial = [{"existing": True}]
        filters, should = apply_collection_filters(
            initial,
            must_not_rapides=True,
            must_only_rapides=False,
            chiffre_clef=True,
        )
        assert len(filters) == 3  # existing + not_rapides + chiffre_clef

    def test_combined_filters(self):
        filters, should = apply_collection_filters(
            [],
            must_not_rapides=True,
            must_only_rapides=False,
            chiffre_clef=True,
            theme="Demographie",
            geo_niveau="DEPARTEMENT",
            geo_keyword="Bretagne",
        )
        assert len(filters) == 4  # not_rapides + chiffre_clef + theme + geo_niveau
        assert len(should) == 2  # geo_keyword multi_match + match_phrase
