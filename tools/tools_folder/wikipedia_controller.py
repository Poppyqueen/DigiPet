from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

from tools.tools_folder.tools_helpers.services.wiki_handle import WikipediaHandle

import time


# Safety floor used when memory_manager is unavailable OR when calc_budgets()
# throws. Intentionally conservative — better to warn the agent about a medium
# article than to silently dump a huge one into context.
# This is a last-resort baseline, not a tuning knob; tune via memory budgets.
_ARTICLE_TOKEN_DANGER_THRESHOLD_FALLBACK = 10_000

# Minimum sleep between agent-triggered API calls to prevent rapid-fire
# requests if the agent gets stuck in a loop.
FETCH_SLEEP_SECONDS = 1.25


class WikipediaController:
    """
    Mediates between the agent's tool calls and Wikipedia_handle.

    Responsibilities:
      - Deduct energy on each action.
      - Fire the signal callback (UI icon popup).
      - Track last query, last full article, and last summary independently
        for display_information() and agent_information().
      - Enforce the article-size danger-alert protocol on full article fetches:
          * The article is ALWAYS fetched from the API first.
          * Its token count is measured via memory_manager.token_manager.count_tokens().
          * If the article exceeds the danger threshold and memory_danger_override
            is False, the content is cached internally and a warning is returned.
          * The agent calls again with memory_danger_override=True to receive
            the cached content — no second API call is made.
      - display_information(): full content + full summary, for UI only.
      - agent_information(): titles + metadata only, no article content.
    """

    def __init__(self, state_manager, signal=None, memory_manager=None):
        self._signal_callback = signal
        self._memory_manager  = memory_manager
        self.wiki             = WikipediaHandle()
        self.state_manager: InventoryHouseManager = state_manager

        # --- Search tracking ---
        self._last_wiki_query_text:    str  = ""
        self._last_wiki_query_results: str  = ""

        # --- Full article tracking ---
        self._last_accessed_title:   str  = ""
        self._last_accessed_content: str  = ""    # display only
        self._full_article_fetched:  bool = False

        # --- Summary tracking ---
        self._last_summary_title:   str  = ""
        self._last_summary_content: str  = ""     # display only
        self._summary_fetched:      bool = False

        # Articles held back due to size, waiting for override
        # key: normalised title (lower-stripped), value: content string
        self._pending_large_articles: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _deduct_energy(self, amount: int) -> None:
        self.state_manager.adjust_stat("energy", amount)

    def _fire_signal(self) -> None:
        if self._signal_callback:
            self._signal_callback({
                "type": "show_icon_popup",
                "icon_path": "style/images/action_icons/computer_icon.png",
            })

    def _count_tokens(self, text: str) -> int:
        """
        Counts tokens via memory_manager.token_manager.count_tokens().

        Returns 0 on any failure so the size check fails open (no false alerts).
        Failures are always printed — a silent fallback here would make the
        danger threshold invisible and hard to debug.
        """
        if self._memory_manager is None:
            print(
                "[WikipediaController] WARNING: memory_manager is None — "
                "token counting unavailable. Article size check will use the "
                f"hard-coded fallback threshold of {_ARTICLE_TOKEN_DANGER_THRESHOLD_FALLBACK:,} tokens."
            )
            return 0
        try:
            return self._memory_manager.token_manager.count_tokens(text)
        except Exception as e:
            print(
                f"[WikipediaController] WARNING: token_manager.count_tokens() raised: {e}\n"
                "Returning 0 — size check will NOT trigger for this article."
            )
            return 0

    def _article_danger_threshold(self) -> int:
        """
        Returns the token ceiling for a single fetched article.

        Primary: calc_budgets()["system_summarize"] — already defined as the
        point at which a single tool message is too large for context. Scales
        automatically with max_tokens_limit.

        Fallback: _ARTICLE_TOKEN_DANGER_THRESHOLD_FALLBACK.
        Always printed when used — a silent fallback defeats the purpose of
        having the threshold at all.
        """
        if self._memory_manager is None:
            print(
                "[WikipediaController] WARNING: memory_manager is None — "
                "cannot derive dynamic article threshold from calc_budgets(). "
                f"Using hard-coded fallback: {_ARTICLE_TOKEN_DANGER_THRESHOLD_FALLBACK:,} tokens."
            )
            return _ARTICLE_TOKEN_DANGER_THRESHOLD_FALLBACK
        try:
            return self._memory_manager.calc_budgets()["system_summarize"]
        except Exception as e:
            print(
                f"[WikipediaController] WARNING: calc_budgets() raised: {e}\n"
                f"Using hard-coded fallback threshold: {_ARTICLE_TOKEN_DANGER_THRESHOLD_FALLBACK:,} tokens."
            )
            return _ARTICLE_TOKEN_DANGER_THRESHOLD_FALLBACK

    @staticmethod
    def _cache_key(title: str) -> str:
        return title.strip().lower()

    # ------------------------------------------------------------------ #
    #  Agent-facing tool functions                                         #
    # ------------------------------------------------------------------ #

    def search_wikipedia_articles(self, query: str) -> str:
        """
        Searches Wikipedia for articles matching `query`.

        Returns a formatted list of up to 10 results with titles and snippets.
        Energy cost: 2.
        """
        time.sleep(FETCH_SLEEP_SECONDS)
        self._deduct_energy(-2)
        self._fire_signal()

        results = self.wiki.search_wikipedia(query)

        self._last_wiki_query_text    = query
        self._last_wiki_query_results = results

        return results

    def get_wikipedia_article_summary(self, title: str) -> str:
        """
        Fetches the introductory summary section of a Wikipedia article.

        Lighter than a full article fetch — useful for a quick overview.
        Energy cost: 3.

        Args:
            title: Exact Wikipedia page title (use search first if unsure).

        Returns:
            Structured string with TITLE and BODY (intro section only).
        """
        time.sleep(FETCH_SLEEP_SECONDS)
        self._deduct_energy(-3)
        self._fire_signal()

        summary = self.wiki.get_wikipedia_summary(title)

        self._last_summary_title   = title
        self._last_summary_content = summary
        self._summary_fetched      = True

        return summary

    def get_wikipedia_article_content(
        self,
        title: str,
        memory_danger_override: bool = False,
    ) -> str:
        """
        Fetches the FULL plain-text content of a Wikipedia article.

        Article-size danger protocol:
          1. The article is ALWAYS fetched from the API (or served from cache).
          2. Its token count is measured.
          3. If tokens > threshold AND memory_danger_override is False, the
             content is stored in an internal cache and a WARNING is returned.
          4. Call again with memory_danger_override=True to get the cached
             content — no second API call, no extra energy cost.

        Energy cost: 5 on the first (API) call.
        Cache-hit override calls cost 0 extra energy — already paid.

        Args:
            title: Exact Wikipedia page title.
            memory_danger_override: Set True to bypass the size alert and
                                    receive the full article from cache.
        """
        cache_key = self._cache_key(title)

        # --- Cache hit: override call after a prior large-article alert ---
        if memory_danger_override and cache_key in self._pending_large_articles:
            content = self._pending_large_articles.pop(cache_key)
            self._last_accessed_title   = title
            self._last_accessed_content = content
            self._full_article_fetched  = True
            return content

        # --- Normal path: fetch from API ---
        time.sleep(FETCH_SLEEP_SECONDS)
        self._deduct_energy(-5)
        self._fire_signal()

        content     = self.wiki.get_wikipedia_content_by_title(title)
        token_count = self._count_tokens(content)
        threshold   = self._article_danger_threshold()

        # --- Size check ---
        if token_count > threshold and not memory_danger_override:
            self._pending_large_articles[cache_key] = content
            return (
                f"\n[LARGE ARTICLE ALERT]\n"
                f"The article '{title}' is {token_count:,} tokens, which exceeds "
                f"the threshold of {threshold:,} tokens.\n\n"
                f"The content has been fetched and held in a local cache.\n\n"
                f"Options:\n"
                f"  1. Call get_wikipedia_article_summary('{title}') for the intro only.\n"
                f"  2. Call get_wikipedia_article_content('{title}', memory_danger_override=True) "
                f"to receive the full cached article without an extra API call.\n"
            )

        # --- Article within size limit (or override on first call) ---
        self._pending_large_articles.pop(cache_key, None)
        self._last_accessed_title   = title
        self._last_accessed_content = content
        self._full_article_fetched  = True

        return content

    # ------------------------------------------------------------------ #
    #  Information surfaces                                                #
    # ------------------------------------------------------------------ #

    def display_information(self) -> str:
        """
        Full details about the last Wikipedia interactions.

        Intended for the UI / display layer ONLY — do NOT feed this to the agent.
        Includes both the last full article content and the last summary content.
        """
        article_block = (
            f"Last fully fetched article:\n{self._last_accessed_content}"
            if self._full_article_fetched and self._last_accessed_content
            else "No full article has been fetched yet this session."
        )

        summary_block = (
            f"Last fetched summary:\n{self._last_summary_content}"
            if self._summary_fetched and self._last_summary_content
            else "No summary has been fetched yet this session."
        )

        return (
            f"=== Wikipedia Display Information ===\n\n"
            f"Last search query:\n  {self._last_wiki_query_text or '(none)'}\n\n"
            f"Last search results:\n{self._last_wiki_query_results or '  (none)'}\n\n"
            f"{article_block}\n\n"
            f"{summary_block}\n"
        )

    def agent_information(self) -> str:
        """
        Lightweight metadata about the last Wikipedia interactions.

        Safe to include in the agent's context — contains NO article content:
          - Last search query + results (titles/snippets only)
          - Whether a full article has been fetched, and its title
          - Whether a summary has been fetched, and its title
        """
        full_fetch_status = (
            f"Yes — '{self._last_accessed_title}'"
            if self._full_article_fetched
            else "No"
        )

        summary_fetch_status = (
            f"Yes — '{self._last_summary_title}'"
            if self._summary_fetched
            else "No"
        )

        return (
            f"=== Wikipedia Endpoint Information ===\n"
            f"Last search query: {self._last_wiki_query_text or '(none)'}\n"
            f"Last search results:\n{self._last_wiki_query_results or '  (none)'}\n"
            f"Full article fetched this session: {full_fetch_status}\n"
            f"Summary fetched this session: {summary_fetch_status}\n"
        )