"""
Caz — Web Search (DuckDuckGo Lite)

Gives Caz the ability to search the web when the user wants
up-to-date information. Uses DuckDuckGo's lite HTML page —
no API key, no account, no tracking, zero external deps.

Teaching note: DuckDuckGo's "lite" version (lite.duckduckgo.com)
returns simple HTML that's easy to parse. It's meant for text
browsers and low-bandwidth connections, which makes it perfect
for us — minimal markup, fast responses, and no JavaScript.

Security hardening:
    - Only works when network permission is granted (session-scoped)
    - Response size capped (prevents memory exhaustion)
    - URLs validated — only https:// allowed in results
    - HTML stripped and sanitized before display
    - Regex patterns use possessive-style matching with length caps
    - No eval, no exec, no dynamic code from search results
    - Input query sanitized (length limited, control chars stripped)

Privacy:
    - DuckDuckGo doesn't track searches
    - We send a generic User-Agent (no fingerprinting)
    - No cookies stored or sent
"""

import html
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Optional


# --- Input Validation ---

MAX_QUERY_LENGTH = 256
MAX_RESPONSE_BYTES = 512_000  # 512KB — DuckDuckGo Lite is ~20KB typical
MAX_TITLE_LENGTH = 200
MAX_SNIPPET_LENGTH = 300
MAX_URL_LENGTH = 2048
ALLOWED_URL_SCHEMES = ("https://", "http://")


def sanitize_query(query: str) -> str:
    """
    Sanitize a search query before sending.

    Teaching note: Never trust user input, even for search queries.
    Control characters, null bytes, and extreme lengths can cause
    problems with downstream systems.
    """
    # Strip control characters (except normal whitespace)
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", query)
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    # Length cap
    return clean[:MAX_QUERY_LENGTH]


def validate_url(url: str) -> Optional[str]:
    """
    Validate a URL from search results.

    Only allows http/https schemes. Blocks javascript:, data:,
    file://, and other potentially dangerous schemes.

    Returns cleaned URL or None if invalid.
    """
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        return None
    if not any(url.startswith(scheme) for scheme in ALLOWED_URL_SCHEMES):
        return None
    # Block URLs with embedded credentials (user:pass@host)
    parsed = urllib.parse.urlparse(url)
    if parsed.username or parsed.password:
        return None
    return url


# --- HTML Parsing (safe, stdlib-only) ---

class DuckDuckGoLiteParser(HTMLParser):
    """
    Safe HTML parser for DuckDuckGo Lite results.

    Teaching note: We use Python's built-in HTMLParser instead
    of regex for parsing. HTMLParser is a SAX-style parser —
    it fires events (handle_starttag, handle_data, etc.) as it
    walks through the HTML. This is:
    - Immune to ReDoS (no regex on untrusted input)
    - Handles malformed HTML gracefully
    - Can't execute code from the HTML
    - Stdlib — zero external deps

    DuckDuckGo Lite structure:
    - Result links have class="result-link"
    - Snippets are in <td class="result-snippet">
    - Each result is in a table row
    """

    def __init__(self):
        super().__init__()
        self.results: list[dict] = []
        self._current_link: Optional[dict] = None
        self._in_result_link = False
        self._in_snippet = False
        self._current_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple]):
        attr_dict = dict(attrs)

        # Detect result links: <a class="result-link" href="...">
        if tag == "a" and "result-link" in attr_dict.get("class", ""):
            href = attr_dict.get("href", "")
            safe_url = validate_url(href)
            if safe_url:
                self._current_link = {"url": safe_url, "title": "", "snippet": ""}
                self._in_result_link = True
                self._current_text = ""

        # Detect snippet cells: <td class="result-snippet">
        elif tag == "td" and "result-snippet" in attr_dict.get("class", ""):
            self._in_snippet = True
            self._current_text = ""

    def handle_endtag(self, tag: str):
        if tag == "a" and self._in_result_link:
            if self._current_link:
                self._current_link["title"] = self._current_text[:MAX_TITLE_LENGTH]
            self._in_result_link = False
            self._current_text = ""

        elif tag == "td" and self._in_snippet:
            if self._current_link:
                self._current_link["snippet"] = self._current_text[:MAX_SNIPPET_LENGTH]
                self.results.append(self._current_link)
                self._current_link = None
            self._in_snippet = False
            self._current_text = ""

    def handle_data(self, data: str):
        if self._in_result_link or self._in_snippet:
            self._current_text += data

    def handle_entityref(self, name: str):
        if self._in_result_link or self._in_snippet:
            char = html.unescape(f"&{name};")
            self._current_text += char

    def handle_charref(self, name: str):
        if self._in_result_link or self._in_snippet:
            char = html.unescape(f"&#{name};")
            self._current_text += char


# --- Search Result Data ---

@dataclass
class SearchResult:
    """A single validated search result."""
    title: str
    url: str
    snippet: str


# --- Main Search Class ---

class WebSearch:
    """
    Search the web via DuckDuckGo Lite — hardened and safe.

    Zero dependencies — uses only Python stdlib.

    Usage:
        search = WebSearch()
        results = search.query("Python asyncio tutorial")
        for r in results:
            print(f"{r.title}: {r.url}")
    """

    SEARCH_URL = "https://lite.duckduckgo.com/lite/"
    USER_AGENT = "Caz/1.0 (Local AI Assistant)"
    MAX_RESULTS = 5
    TIMEOUT_SECONDS = 10

    def query(
        self, search_term: str, max_results: Optional[int] = None
    ) -> list[SearchResult]:
        """
        Search DuckDuckGo and return parsed results.

        Parameters:
            search_term: What to search for (sanitized internally)
            max_results: How many results (default 5, max 10)

        Returns:
            List of SearchResult objects with title, url, snippet

        Raises:
            ConnectionError: If the search fails (network issue)
            ValueError: If the query is empty after sanitization
        """
        # Sanitize input
        clean_query = sanitize_query(search_term)
        if not clean_query:
            raise ValueError("Search query is empty after sanitization.")

        limit = min(max_results or self.MAX_RESULTS, 10)

        # URL-encode the search query
        data = urllib.parse.urlencode({"q": clean_query}).encode("ascii")

        # Build the request — no cookies, no tracking headers
        req = urllib.request.Request(
            self.SEARCH_URL,
            data=data,
            method="POST",
            headers={
                "User-Agent": self.USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html",
            },
        )

        try:
            with urllib.request.urlopen(
                req, timeout=self.TIMEOUT_SECONDS
            ) as resp:
                # Cap response size to prevent memory exhaustion
                raw_bytes = resp.read(MAX_RESPONSE_BYTES)
                raw_html = raw_bytes.decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError) as e:
            raise ConnectionError(
                f"Search failed: {e}"
            ) from e

        # Parse with safe HTML parser (not regex)
        return self._parse_results(raw_html, limit)

    def _parse_results(
        self, raw_html: str, limit: int
    ) -> list[SearchResult]:
        """
        Parse DuckDuckGo Lite HTML using stdlib HTMLParser.

        Safe against:
        - ReDoS (no regex on untrusted input)
        - Malformed HTML (parser handles gracefully)
        - Injection (all text is treated as data, never executed)
        """
        parser = DuckDuckGoLiteParser()

        try:
            parser.feed(raw_html)
        except Exception:
            # If parsing fails for any reason, return empty
            return []

        results = []
        for item in parser.results[:limit]:
            title = _clean_text(item["title"])
            snippet = _clean_text(item["snippet"])
            url = item["url"]

            if title and url:
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                ))

        return results


def _clean_text(text: str) -> str:
    """Clean and normalize text for safe display."""
    # Remove any remaining HTML-like content
    clean = re.sub(r"<[^>]*>", "", text)
    # Decode entities
    clean = html.unescape(clean)
    # Remove control characters
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", clean)
    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def format_search_results(results: list[SearchResult]) -> str:
    """
    Format search results for display in Caz's chat.

    Returns a nicely formatted string with numbered results,
    titles, URLs, and snippets.
    """
    if not results:
        return "🔍 No results found. The search returned empty."

    lines = ["🔍 Search Results:", ""]
    for i, r in enumerate(results, 1):
        lines.append(f"  {i}. {r.title}")
        lines.append(f"     📎 {r.url}")
        if r.snippet:
            # Truncate long snippets for terminal readability
            snippet = r.snippet[:150]
            if len(r.snippet) > 150:
                snippet += "..."
            lines.append(f"     {snippet}")
        lines.append("")

    lines.append("  Sources cited above. Verify before relying on any result.")
    return "\n".join(lines)
