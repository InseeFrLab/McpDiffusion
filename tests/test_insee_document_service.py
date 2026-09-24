"""Unit tests for mcpdiffusion.services.insee_document."""

import httpx
import pytest
from fastmcp.exceptions import ToolError

from mcpdiffusion.config.settings import Settings
from mcpdiffusion.models.insee import GetInseeDocumentInput
from mcpdiffusion.services.insee_document import (
    _as_relative,
    _fetch_html,
    _format_sommaire,
    _parse_sommaire,
    _truncate,
    get_insee_document,
)
from tests.conftest import FakeAsyncClient

_SETTINGS = Settings(INSEE_BASE_URL="https://www.insee.fr", _env_file=None)


# ===================================================================
# _as_relative
# ===================================================================


class TestAsRelative:
    def test_path_only(self):
        assert _as_relative("https://www.insee.fr/fr/statistiques/123") == "/fr/statistiques/123"

    def test_with_query_string(self):
        result = _as_relative("https://www.insee.fr/fr/statistiques/123?sommaire=456")
        assert result == "/fr/statistiques/123?sommaire=456"

    def test_already_relative(self):
        assert _as_relative("/fr/statistiques/123") == "/fr/statistiques/123"


# ===================================================================
# _truncate
# ===================================================================


class TestTruncate:
    def test_short_text_not_truncated(self):
        text, truncated = _truncate("Short text")
        assert text == "Short text"
        assert truncated is False

    def test_exact_limit_not_truncated(self):
        text = "x" * 1000
        result, truncated = _truncate(text, limit=1000)
        assert truncated is False
        assert result == text

    def test_long_text_truncated(self):
        text = "x" * 5000
        result, truncated = _truncate(text, limit=1000)
        assert truncated is True
        assert len(result) < len(text)
        assert "CONTENT TRUNCATED" in result

    def test_preserves_head_and_tail(self):
        text = "HEAD" + "x" * 5000 + "TAIL"
        result, truncated = _truncate(text, limit=1000)
        assert truncated is True
        assert result.startswith("HEAD")
        assert result.endswith("TAIL")


# ===================================================================
# _parse_sommaire
# ===================================================================


class TestParseSommaire:
    def test_empty_html_returns_empty(self):
        assert _parse_sommaire("<html><body></body></html>", "https://www.insee.fr") == []

    def test_no_sommaire_section_returns_empty(self):
        html = "<html><body><div>Content</div></body></html>"
        assert _parse_sommaire(html, "https://www.insee.fr") == []

    def test_parses_categorized_links(self):
        html = """
        <html><body>
        <div class="sommaire">
            <ul class="sommaire">
                <li>
                    <h2>Category A</h2>
                    <ul class="sommaire">
                        <li class="lien-produit"><a href="/fr/stat/1">Link 1</a></li>
                        <li class="lien-produit"><a href="/fr/stat/2">Link 2</a></li>
                    </ul>
                </li>
            </ul>
        </div>
        </body></html>
        """
        result = _parse_sommaire(html, "https://www.insee.fr")
        assert len(result) == 2
        assert result[0]["category"] == "Category A"
        assert result[0]["title"] == "Link 1"
        assert result[0]["url"] == "/fr/stat/1"
        assert result[1]["title"] == "Link 2"

    def test_parses_uncategorized_links(self):
        html = """
        <html><body>
        <div class="sommaire">
            <ul class="sommaire">
                <li><a href="/fr/stat/2">Direct Link</a></li>
            </ul>
        </div>
        </body></html>
        """
        result = _parse_sommaire(html, "https://www.insee.fr")
        assert len(result) == 1
        assert result[0]["category"] == ""
        assert result[0]["title"] == "Direct Link"

    def test_no_ul_inside_sommaire_returns_empty(self):
        html = """
        <html><body>
        <div class="sommaire"><p>No list here</p></div>
        </body></html>
        """
        assert _parse_sommaire(html, "https://www.insee.fr") == []


# ===================================================================
# _format_sommaire
# ===================================================================


class TestFormatSommaire:
    def test_groups_by_category(self):
        items = [
            {"category": "A", "title": "T1", "url": "/1"},
            {"category": "A", "title": "T2", "url": "/2"},
            {"category": "B", "title": "T3", "url": "/3"},
        ]
        result = _format_sommaire(items)
        assert result == {"A": {"T1": "/1", "T2": "/2"}, "B": {"T3": "/3"}}

    def test_empty_list(self):
        assert _format_sommaire([]) == {}

    def test_empty_category(self):
        items = [{"category": "", "title": "T1", "url": "/1"}]
        result = _format_sommaire(items)
        assert result == {"": {"T1": "/1"}}


# ===================================================================
# _fetch_html
# ===================================================================


class TestFetchHtml:
    async def test_success_returns_html(self):
        fake = FakeAsyncClient(
            lambda url, **kw: httpx.Response(
                200,
                content=b"<html>OK</html>",
                request=httpx.Request("GET", url),
            )
        )
        result = await _fetch_html("/fr/stat/1", _SETTINGS, fake)
        assert result == "<html>OK</html>"

    async def test_prepends_base_url_for_relative_path(self):
        captured = []

        def handler(url, **kw):
            captured.append(url)
            return httpx.Response(200, content=b"ok", request=httpx.Request("GET", url))

        await _fetch_html("/fr/stat/1", _SETTINGS, FakeAsyncClient(handler))
        assert captured[0] == "https://www.insee.fr/fr/stat/1"

    async def test_absolute_url_not_modified(self):
        captured = []

        def handler(url, **kw):
            captured.append(url)
            return httpx.Response(200, content=b"ok", request=httpx.Request("GET", url))

        await _fetch_html("https://other.fr/page", _SETTINGS, FakeAsyncClient(handler))
        assert captured[0] == "https://other.fr/page"

    async def test_timeout_raises_tool_error(self):
        def handler(url, **kw):
            raise httpx.TimeoutException("timed out")

        with pytest.raises(ToolError, match="BACKEND_UNAVAILABLE"):
            await _fetch_html("/fr/stat/1", _SETTINGS, FakeAsyncClient(handler))

    async def test_404_raises_tool_error(self):
        def handler(url, **kw):
            resp = httpx.Response(404, content=b"Not Found", request=httpx.Request("GET", url))
            raise httpx.HTTPStatusError("Not Found", request=resp.request, response=resp)

        with pytest.raises(ToolError, match="NOT_FOUND"):
            await _fetch_html("/fr/stat/1", _SETTINGS, FakeAsyncClient(handler))

    async def test_500_raises_tool_error(self):
        def handler(url, **kw):
            resp = httpx.Response(500, content=b"Error", request=httpx.Request("GET", url))
            raise httpx.HTTPStatusError("Error", request=resp.request, response=resp)

        with pytest.raises(ToolError, match="UPSTREAM_ERROR"):
            await _fetch_html("/fr/stat/1", _SETTINGS, FakeAsyncClient(handler))


# ===================================================================
# get_insee_document
# ===================================================================


class TestGetInseeDocument:
    async def test_empty_url_list_raises(self):
        params = GetInseeDocumentInput(list_of_url=[])
        with pytest.raises(ToolError, match="INVALID_INPUT"):
            await get_insee_document(params, http_client=FakeAsyncClient(), settings=_SETTINGS)

    async def test_fetch_error_returns_error_result(self):
        def handler(url, **kw):
            raise httpx.TimeoutException("timed out")

        params = GetInseeDocumentInput(list_of_url=["/fr/stat/1"])
        result = await get_insee_document(
            params,
            http_client=FakeAsyncClient(handler),
            settings=_SETTINGS,
        )

        assert result.count == 1
        assert result.results[0].status == "error"
        assert "ToolError" in result.results[0].error

    async def test_success_returns_markdown(self):
        html = "<html><body><article><p>Important paragraph.</p></article></body></html>"
        fake = FakeAsyncClient(
            lambda url, **kw: httpx.Response(
                200,
                content=html.encode(),
                request=httpx.Request("GET", url),
            )
        )
        params = GetInseeDocumentInput(
            list_of_url=["/fr/stat/1"],
            include_sommaire=False,
            truncate_content=False,
        )
        result = await get_insee_document(params, http_client=fake, settings=_SETTINGS)

        assert result.count == 1
        assert result.results[0].status == "success"
        assert result.results[0].error is None

    async def test_multiple_urls(self):
        fake = FakeAsyncClient(
            lambda url, **kw: httpx.Response(
                200,
                content=b"<html><body><p>Content</p></body></html>",
                request=httpx.Request("GET", url),
            )
        )
        params = GetInseeDocumentInput(
            list_of_url=["/fr/stat/1", "/fr/stat/2"],
            include_sommaire=False,
        )
        result = await get_insee_document(params, http_client=fake, settings=_SETTINGS)
        assert result.count == 2

    async def test_mixed_success_and_error(self):
        call_count = [0]

        def handler(url, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return httpx.Response(
                    200,
                    content=b"<html><body><p>OK</p></body></html>",
                    request=httpx.Request("GET", url),
                )
            raise httpx.TimeoutException("timed out")

        params = GetInseeDocumentInput(
            list_of_url=["/fr/stat/ok", "/fr/stat/fail"],
            include_sommaire=False,
        )
        result = await get_insee_document(
            params,
            http_client=FakeAsyncClient(handler),
            settings=_SETTINGS,
        )
        assert result.count == 2
        assert result.results[0].status == "success"
        assert result.results[1].status == "error"
