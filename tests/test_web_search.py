"""
Tests for Caz's web search module.

Verifies that:
- Query sanitization removes dangerous characters
- URL validation blocks non-http(s) schemes
- HTML parsing extracts results safely
- Empty/malformed input handled gracefully
- Format function produces readable output
"""

from core.web_search import (
    SearchResult,
    WebSearch,
    format_search_results,
    sanitize_query,
    validate_url,
)


# --- Input Sanitization Tests ---

def test_sanitize_query_strips_control_chars():
    """Control characters are removed from queries."""
    assert sanitize_query("hello\x00world") == "helloworld"
    assert sanitize_query("test\x07\x08query") == "testquery"


def test_sanitize_query_normalizes_whitespace():
    """Excessive whitespace is collapsed."""
    assert sanitize_query("  lots   of   spaces  ") == "lots of spaces"


def test_sanitize_query_caps_length():
    """Queries longer than 256 chars are truncated."""
    long_query = "a" * 500
    result = sanitize_query(long_query)
    assert len(result) == 256


def test_sanitize_query_preserves_unicode():
    """Unicode characters in queries are preserved."""
    assert sanitize_query("日本語テスト") == "日本語テスト"


def test_sanitize_query_empty_returns_empty():
    """Empty or whitespace-only queries return empty."""
    assert sanitize_query("") == ""
    assert sanitize_query("   ") == ""


# --- URL Validation Tests ---

def test_validate_url_allows_https():
    """HTTPS URLs are valid."""
    assert validate_url("https://example.com/page") == "https://example.com/page"


def test_validate_url_allows_http():
    """HTTP URLs are valid (some sites don't have HTTPS)."""
    assert validate_url("http://example.com") == "http://example.com"


def test_validate_url_blocks_javascript():
    """javascript: scheme is blocked."""
    assert validate_url("javascript:alert(1)") is None


def test_validate_url_blocks_data():
    """data: scheme is blocked."""
    assert validate_url("data:text/html,<script>alert(1)</script>") is None


def test_validate_url_blocks_file():
    """file:// scheme is blocked."""
    assert validate_url("file:///etc/passwd") is None


def test_validate_url_blocks_ftp():
    """ftp:// scheme is blocked."""
    assert validate_url("ftp://malicious.com/payload") is None


def test_validate_url_blocks_credentials():
    """URLs with embedded credentials are blocked."""
    assert validate_url("https://user:pass@evil.com") is None


def test_validate_url_blocks_too_long():
    """Extremely long URLs are blocked."""
    long_url = "https://example.com/" + "a" * 3000
    assert validate_url(long_url) is None


def test_validate_url_strips_whitespace():
    """Leading/trailing whitespace is stripped."""
    assert validate_url("  https://example.com  ") == "https://example.com"


# --- HTML Parsing Tests ---

def test_parser_handles_empty_html():
    """Empty HTML returns empty results."""
    search = WebSearch()
    results = search._parse_results("", 5)
    assert results == []


def test_parser_handles_malformed_html():
    """Malformed HTML doesn't crash, returns empty."""
    search = WebSearch()
    results = search._parse_results("<<<<>>>><//>><", 5)
    assert isinstance(results, list)


def test_parser_handles_no_results_page():
    """HTML without result elements returns empty."""
    html = "<html><body><p>No results found</p></body></html>"
    search = WebSearch()
    results = search._parse_results(html, 5)
    assert results == []


# --- Format Tests ---

def test_format_empty_results():
    """Empty result list shows helpful message."""
    output = format_search_results([])
    assert "No results found" in output


def test_format_results_includes_all_fields():
    """Formatted output includes title, url, snippet."""
    results = [
        SearchResult(
            title="Test Page",
            url="https://example.com",
            snippet="This is a test snippet.",
        )
    ]
    output = format_search_results(results)
    assert "Test Page" in output
    assert "https://example.com" in output
    assert "test snippet" in output


def test_format_results_truncates_long_snippets():
    """Snippets longer than 150 chars are truncated."""
    results = [
        SearchResult(
            title="Long",
            url="https://example.com",
            snippet="x" * 200,
        )
    ]
    output = format_search_results(results)
    assert "..." in output


def test_format_results_shows_citation_reminder():
    """Output includes reminder to verify sources."""
    results = [
        SearchResult(title="T", url="https://x.com", snippet="S")
    ]
    output = format_search_results(results)
    assert "Verify" in output


if __name__ == "__main__":
    test_sanitize_query_strips_control_chars()
    test_sanitize_query_normalizes_whitespace()
    test_sanitize_query_caps_length()
    test_sanitize_query_preserves_unicode()
    test_sanitize_query_empty_returns_empty()
    test_validate_url_allows_https()
    test_validate_url_allows_http()
    test_validate_url_blocks_javascript()
    test_validate_url_blocks_data()
    test_validate_url_blocks_file()
    test_validate_url_blocks_ftp()
    test_validate_url_blocks_credentials()
    test_validate_url_blocks_too_long()
    test_validate_url_strips_whitespace()
    test_parser_handles_empty_html()
    test_parser_handles_malformed_html()
    test_parser_handles_no_results_page()
    test_format_empty_results()
    test_format_results_includes_all_fields()
    test_format_results_truncates_long_snippets()
    test_format_results_shows_citation_reminder()
    print("✅ All web search tests passed!")
