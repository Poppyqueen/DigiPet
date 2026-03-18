import time
import textwrap
import re
import html
import os

import requests_cache
from retry_requests import retry
from dotenv import load_dotenv


# 1-hour cache stored alongside other service caches for consistency.
os.makedirs(".cache", exist_ok=True)
_cache_session = requests_cache.CachedSession(
    ".cache/wikipedia",
    backend="filesystem",
    expire_after=3600, # 1 hour in seconds
)
# Delete any entries that have already expired sitting on disk.
# Runs once at import time — cheap, keeps the cache from accumulating orphans.
_cache_session.cache.delete(expired=True)
_session = retry(_cache_session, retries=5, backoff_factor=0.2)


class WikipediaHandle:
    """
    Thin wrapper around the Wikipedia API.

    All requests go through a requests_cache CachedSession (1-hour TTL,
    filesystem backend) so repeated lookups for the same title/query are
    served from disk without hitting the network. Retry logic (up to 5
    attempts, exponential back-off) is layered on top via retry_requests,
    matching the openmeteo service pattern.

    Memory management and danger-alert logic live entirely in
    WikipediaController — this class just fetches and returns strings.
    """

    def __init__(self):
        self.wiki_url = "https://en.wikipedia.org/w/api.php"
        load_dotenv()
        self.app_name = os.environ.get("WIKIPEDIA_APP_NAME")
        self.wikipedia_contact = os.environ.get("WIKIPEDIA_CONTACT")

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _call_wiki_api(self, params: dict) -> dict:
        """
        GET request to the Wikipedia API via the cached + retry session.

        Cache behaviour:
          - Cache key is derived from the full URL + params by requests_cache.
          - Cached responses are returned instantly — no network call, no sleep.
          - Fresh (uncached) responses sleep 1 second after returning to
            respect Wikipedia's rate-limit guidance.

        Args:
            params: API parameters. 'format' is always forced to 'json'.

        Returns:
            Parsed JSON response dict.

        Raises:
            requests.exceptions.RequestException: Network / HTTP errors.
            ValueError: Non-JSON response body.
        """
        params["format"] = "json"
        headers = {
            "User-Agent": f"{self.app_name}/1.0 ({self.wikipedia_contact})"
        }

        response = _session.get(self.wiki_url, params=params, headers=headers)
        response.raise_for_status()

        # Only rate-limit sleep on real network hits; cached responses are free.
        if not getattr(response, "from_cache", False):
            time.sleep(1)

        return response.json()

    def _clean_html(self, text: str) -> str:
        """Strips HTML tags and decodes entities. Used on search snippets."""
        if not isinstance(text, str):
            return text
        cleaned = html.unescape(text)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        cleaned = re.sub(r"^\* ", "- ", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^: ",  "  ", cleaned, flags=re.MULTILINE)
        return cleaned

    # ------------------------------------------------------------------ #
    #  Public API methods                                                  #
    # ------------------------------------------------------------------ #

    def search_wikipedia(self, query: str) -> str:
        """
        Searches Wikipedia and returns a formatted string of up to 10 results.

        Args:
            query: Search term.

        Returns:
            Formatted string with titles and cleaned snippets, or an error message.
        """
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srprop": "snippet|pageid",
            "srlimit": 10,
        }

        parts = []
        try:
            data    = self._call_wiki_api(params)
            results = data.get("query", {}).get("search", None)

            if results is None:
                print(f"[Wikipedia_handle] Warning: unexpected search response for '{query}': {data}")
                return f"Error: Could not parse search results for '{query}'. Unexpected API response."

            if not results:
                return f"No search results found for '{query}'. Please try another query."

            parts.append(f"Search results for '{query}':\n")
            parts.append("-" * 30 + "\n")

            for i, item in enumerate(results):
                title   = item.get("title", "N/A")
                snippet = self._clean_html(item.get("snippet", "No snippet available"))
                wrapped = "\n    ".join(textwrap.wrap(snippet, width=80))
                parts.append(f"{i + 1}. Title: {title}\n")
                parts.append(f"   Snippet: {wrapped}...\n")
                parts.append("-" * 10 + "\n")

            parts.append(f"Total results found: {len(results)}\n")

        except Exception as e:
            print(f"[Wikipedia_handle] Error in search_wikipedia for '{query}': {e}")
            parts.append(f"An error occurred while searching for '{query}': {e}")

        return "".join(parts)

    def get_wikipedia_content_by_title(self, title: str) -> str:
        """
        Fetches the FULL plain-text extract for a Wikipedia page.

        No size/memory checks here — WikipediaController handles that layer.

        Returns:
            Structured string:
                TITLE: <title>
                BODY:
                <full plain-text extract>
        """
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": 1,
            "exlimit": 1,
            "redirects": 1,
            "uselang": "en",
        }

        page_title_out = title
        body_out       = f"Attempted to retrieve content for '{title}'..."

        try:
            data  = self._call_wiki_api(params)
            pages = data.get("query", {}).get("pages", None)

            if pages is None:
                print(f"[Wikipedia_handle] Warning: unexpected content response for '{title}': {data}")
                body_out = f"Error: Could not parse content response for '{title}'. Unexpected API response."
            else:
                page_id   = next(iter(pages))
                page_data = pages[page_id]

                if page_id == "-1":
                    body_out = f"Wikipedia page '{title}' not found or ambiguous."
                else:
                    page_title_out = page_data.get("title", title)
                    extract        = page_data.get("extract", "")
                    body_out       = extract if extract else f"No text extract available for '{page_title_out}'."

        except Exception as e:
            print(f"[Wikipedia_handle] Error in get_wikipedia_content_by_title for '{title}': {e}")
            body_out = f"An error occurred while fetching content for '{title}': {e}"

        return f"\nTITLE: {page_title_out}\nBODY:\n{body_out}\n"

    def get_wikipedia_summary(self, title: str) -> str:
        """
        Fetches only the introductory section (lead) of a Wikipedia page.

        Uses exintro=1 so the API returns only the opening paragraphs.

        Returns:
            Structured string:
                TITLE: <title> (SUMMARY ONLY)
                BODY:
                <intro plain-text extract>
        """
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "exlimit": 1,
            "redirects": 1,
        }

        page_title_out = title
        body_out       = f"Attempted to retrieve summary for '{title}'..."

        try:
            data  = self._call_wiki_api(params)
            pages = data.get("query", {}).get("pages", None)

            if pages is None:
                print(f"[Wikipedia_handle] Warning: unexpected summary response for '{title}': {data}")
                body_out = f"Error: Could not parse summary response for '{title}'. Unexpected API response."
            else:
                page_id   = next(iter(pages))
                page_data = pages[page_id]

                if page_id == "-1":
                    body_out = f"Wikipedia page '{title}' not found or ambiguous."
                else:
                    page_title_out = page_data.get("title", title)
                    extract        = page_data.get("extract", "")
                    body_out       = extract if extract else f"No summary available for '{page_title_out}'."

        except Exception as e:
            print(f"[Wikipedia_handle] Error in get_wikipedia_summary for '{title}': {e}")
            body_out = f"An error occurred while fetching summary for '{title}': {e}"

        return f"\nTITLE: {page_title_out} (SUMMARY ONLY)\nBODY:\n{body_out}\n"

    def fetch_random_wiki_article(self) -> str:
        """
        Fetches a random Wikipedia page and returns its full content.

        The random-title call is NOT cached (a different result every time is
        the point), but the subsequent content fetch IS cached — so if the same
        title comes up again within an hour it costs nothing.

        Returns:
            Same structured string as get_wikipedia_content_by_title.
        """
        params = {
            "action": "query",
            "list": "random",
            "rnnamespace": "0",
            "rnlimit": "1",
        }

        try:
            data        = self._call_wiki_api(params)
            random_list = data.get("query", {}).get("random", [])

            if not random_list:
                raise ValueError("Failed to get random page title from API response.")

            page_title = random_list[0]["title"]
            return self.get_wikipedia_content_by_title(page_title)

        except Exception as e:
            print(f"[Wikipedia_handle] Error in fetch_random_wiki_article: {e}")
            return f"\nTITLE: Error Fetching Random Article\nBODY:\nFailed to fetch a random article: {e}\n"