"""
bluesky_client/helpers/feed.py

Read-only feed exploration. Returns Page[T] envelopes throughout so every
list operation the LLM calls feels identical from a pagination standpoint.

Feed registry:
    A dict of human-readable name → AT URI is maintained on the class.
    The LLM calls list_feeds() to see what's available, then passes a name
    to get_feed(). Raw AT URIs still work as an escape hatch.

    To find a feed URI manually:
        1. Open bsky.app, navigate to any feed generator page.
        2. The URL is: https://bsky.app/profile/<handle>/feed/<slug>
        3. The AT URI is: at://<did>/app.bsky.feed.generator/<slug>
        4. To resolve <handle> → <did>, use:
               client.com.atproto.identity.resolve_handle({'handle': '<handle>'})
           or just browse to the feed, open dev-tools → Network → look for the
           getFeedGenerator call which contains the full AT URI.

Thread "pagination" via depth:
    Bluesky threads are fetched as a nested tree, not a cursor-paged list.
    To expose a consistent pagination interface, we map page number to depth:

        page 1 → depth DEPTH_PER_PAGE * 1   (immediate replies visible)
        page 2 → depth DEPTH_PER_PAGE * 2   (replies-to-replies visible)
        ...

    has_more is True when the tree contains truncated nodes — i.e. a reply
    node whose `replies` field is None (not fetched) rather than [] (empty).
    The LLM requests page 2 if it needs to see deeper into the thread.
"""



from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Union, Tuple

from atproto import models

from .pagination import Page

if TYPE_CHECKING:
    from ...bluesky_bot.client import BskyBotClient

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 7
DEPTH_PER_PAGE = 4   # replies depth added per "page" for thread fetching
MAX_DEPTH = 20       # atproto API ceiling for parentHeight / depth params

# ---------------------------------------------------------------------------
# Feed registry — human-readable name → AT URI
#
# URIs verified at time of writing. Add your own 
# ---------------------------------------------------------------------------


_DEFAULT_FEEDS: Dict[str, str] = {
    "whats-hot": "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot", # Source: https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur/feed/whats-hot
    "for-science": "at://did:plc:jfhpnnst6flqway4eaeqzj2a/app.bsky.feed.generator/for-science", # Source: https://bsky.app/profile/bossett.social/feed/for-science
    "verified-news": "at://did:plc:kkf4naxqmweop7dv4l2iqqf5/app.bsky.feed.generator/verified-news", # Source: https://bsky.app/profile/aendra.com/feed/verified-news
    "neuroskyence": "at://did:plc:nylio5rpw7u3wtven3vcriam/app.bsky.feed.generator/aaai4amp77qp6", # Source: https://bsky.app/profile/micahgallen.com/feed/aaai4amp77qp6
    "catch-up": "at://did:plc:tenurhgjptubkk5zf5qhi3og/app.bsky.feed.generator/catch-up", # Source: https://bsky.app/profile/did:plc:tenurhgjptubkk5zf5qhi3og/feed/catch-up
    "AI-A": "at://did:plc:ugbenc43qu4v3hemephm2cry/app.bsky.feed.generator/aaamqhwmov3y4", # Source: https://bsky.app/profile/raefmeeuwisse.bsky.social/feed/aaamqhwmov3y4
    "AI-B": "at://did:plc:lyrmsmhhg7vzz4ghj44y5xzq/app.bsky.feed.generator/98c5c425c773", # Source: https://bsky.app/profile/track.goodfeeds.co/feed/98c5c425c773
    "bsky-team": "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/bsky-team", # Source: https://bsky.app/profile/bsky.app/feed/bsky-team
    "for-you": "at://did:plc:3guzzweuqraryl3rdkimjamk/app.bsky.feed.generator/for-you", # Source: https://bsky.app/profile/spacecowboy17.bsky.social/feed/for-you
}



class FeedHelper:
    """
    Read-only feed access with uniform Page[T] pagination.

    Feed registry usage:
        bot.feed.list_feeds()                    # see available names
        bot.feed.get_feed("whats-hot")           # fetch by name
        bot.feed.register("my-feed", "at://...") # add at runtime
        bot.feed.get_feed("my-feed", page=2, cursor=prev.cursor)

    Thread "pagination":
        page1 = bot.feed.get_thread(uri)
        if page1.has_more:
            page2 = bot.feed.get_thread(uri, page=2)
    """

    def __init__(self, bot: "BskyBotClient") -> None:
        self._bot = bot
        # Instance-level copy so registrations don't bleed across bot instances
        self._feeds: Dict[str, str] = dict(_DEFAULT_FEEDS)

    # ------------------------------------------------------------------
    # Feed registry
    # ------------------------------------------------------------------

    def list_feeds(self) -> Dict[str, str]:
        """
        Return the registry of available feed names and their AT URIs.

        The LLM should call this before get_feed() to know valid names.
        """
        return dict(self._feeds)

    def register(self, name: str, uri: str) -> None:
        """
        Add a feed to the registry at runtime.

        Args:
            name: Human-readable key (e.g. 'my-tech-feed').
            uri:  AT URI of the feed generator.
        """
        self._feeds[name] = uri
        logger.info("Feed registered: '%s' → %s", name, uri)

    def unregister(self, name: str) -> bool:
        """Remove a feed from the registry. Returns True if it existed."""
        if name in self._feeds:
            del self._feeds[name]
            logger.info("Feed unregistered: '%s'", name)
            return True
        return False

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def get_timeline(
        self,
        limit: int = DEFAULT_LIMIT,
        cursor: Optional[str] = None,
        page: int = 1,
        algorithm: str = "reverse-chronological",
    ) -> Page[models.AppBskyFeedDefs.FeedViewPost]:
        """
        Return a page of the bot account's home timeline.

        Args:
            limit:     Items per page (max 100).
            cursor:    Opaque cursor from a previous Page for next page.
            page:      Page number for tracking.
            algorithm: Feed algorithm; 'reverse-chronological' is default.

        Returns:
            Page[FeedViewPost].
        """
        response = self._bot.raw.get_timeline(
            algorithm=algorithm, limit=limit, cursor=cursor
        )
        result = Page(
            items=list(response.feed),
            cursor=response.cursor,
            page=page,
        )
        logger.debug("get_timeline page=%d: %d posts, has_more=%s", page, result.count, result.has_more)
        return result

    # ------------------------------------------------------------------
    # Feed generator
    # ------------------------------------------------------------------

    def get_feed(
        self,
        name_or_uri: str,
        limit: int = DEFAULT_LIMIT,
        cursor: Optional[str] = None,
        page: int = 1,
    ) -> Page[models.AppBskyFeedDefs.FeedViewPost]:
        """
        Return a page of posts from a named feed or a raw AT URI.

        Args:
            name_or_uri: A registry name (e.g. 'whats-hot') or a raw AT URI.
            limit:       Items per page.
            cursor:      Opaque cursor from a previous Page for next page.
            page:        Page number for tracking.

        Returns:
            Page[FeedViewPost].

        Raises:
            KeyError: If name_or_uri is a name not in the registry.
        """
        uri = self._resolve_feed_uri(name_or_uri)
        try:
            response = self._bot.raw.app.bsky.feed.get_feed(
                models.AppBskyFeedGetFeed.Params(feed=uri, limit=limit, cursor=cursor)
            )
            result = Page(items=list(response.feed), cursor=response.cursor, page=page)
            logger.debug(
                "get_feed('%s') page=%d: %d posts, has_more=%s",
                name_or_uri, page, result.count, result.has_more,
            )
            return result
        except Exception as exc:
            logger.error("get_feed('%s') failed: %s", name_or_uri, exc)
            return Page(items=[], cursor=None, page=page)

    # ------------------------------------------------------------------
    # Author posts
    # ------------------------------------------------------------------

    def get_author_posts(
        self,
        actor: str,
        limit: int = DEFAULT_LIMIT,
        cursor: Optional[str] = None,
        page: int = 1,
    ) -> Page[models.AppBskyFeedDefs.FeedViewPost]:
        """
        Return a page of posts from a specific author.

        Args:
            actor:  Handle (e.g. 'user.bsky.social') or DID.
            limit:  Items per page.
            cursor: Opaque cursor from a previous Page for next page.
            page:   Page number for tracking.

        Returns:
            Page[FeedViewPost].
        """
        response = self._bot.raw.get_author_feed(actor=actor, limit=limit, cursor=cursor)
        result = Page(items=list(response.feed), cursor=response.cursor, page=page)
        logger.debug(
            "get_author_posts('%s') page=%d: %d posts, has_more=%s",
            actor, page, result.count, result.has_more,
        )
        return result

    # ------------------------------------------------------------------
    # Thread — depth mapped to pages
    # ------------------------------------------------------------------


    def get_thread(
        self,
        uri: str,
        limit: int = DEFAULT_LIMIT,
        page: int = 1,
    ) -> Page[Tuple[models.AppBskyFeedDefs.ThreadViewPost, int]]:
        """
        Fetch a post thread. Flattens the tree and paginates using strict offsets
        to prevent massive token-bomb payloads from highly active threads.

        Returns:
            Page[Tuple[ThreadViewPost, depth_int]]
        """
        try:
            response = self._bot.raw.app.bsky.feed.get_post_thread(
                models.AppBskyFeedGetPostThread.Params(uri=uri, depth=MAX_DEPTH)
            )
        except Exception as exc:
            logger.error("get_thread('%s') page=%d failed: %s", uri, page, exc)
            return Page(items=[], cursor=None, page=page, _has_more_hint=False)

        thread_post = response.thread
        if not isinstance(thread_post, models.AppBskyFeedDefs.ThreadViewPost):
            logger.warning("get_thread: unexpected thread type %s", type(thread_post))
            return Page(items=[], cursor=None, page=page, _has_more_hint=False)

        # Flatten tree using Depth First Search
        flat_nodes = self._flatten_thread(thread_post, current_depth=0)

        # Apply strict offset pagination
        start = (page - 1) * limit
        end = start + limit
        sliced_items = flat_nodes[start:end]

        # has_more: True if there are more flat nodes, OR if the API truncated deeper replies
        has_more = (len(flat_nodes) > end) or self._tree_is_truncated(thread_post)

        result = Page(
            items=sliced_items,
            cursor=None,         # threads use offset via `page`, not cursor
            page=page,
            _has_more_hint=has_more,
        )
        logger.debug(
            "get_thread('%s') page=%d: returned %d limit, has_more=%s",
            uri, page, result.count, result.has_more,
        )
        return result

    def _flatten_thread(
        self, 
        node: models.AppBskyFeedDefs.ThreadViewPost, 
        current_depth: int = 0
    ) -> List[Tuple[models.AppBskyFeedDefs.ThreadViewPost, int]]:
        """Recursively flattens the thread tree into a linear list of (node, depth) tuples."""
        out = [(node, current_depth)]
        if node.replies:
            for r in node.replies:
                if isinstance(r, models.AppBskyFeedDefs.ThreadViewPost):
                    out.extend(self._flatten_thread(r, current_depth + 1))
        return out

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def format_post(self, feed_view: models.AppBskyFeedDefs.FeedViewPost) -> str:
        """One-liner for a FeedViewPost — handy for logging."""
        author = feed_view.post.author.handle
        text = feed_view.post.record.text.replace("\n", " ")
        return f"@{author}: {text}"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resolve_feed_uri(self, name_or_uri: str) -> str:
        """
        Resolve a registry name to an AT URI, or pass through a raw URI.
        Raises KeyError with a helpful message if the name is unknown.
        """
        if name_or_uri.startswith("at://"):
            return name_or_uri
        if name_or_uri in self._feeds:
            return self._feeds[name_or_uri]
        available = ", ".join(sorted(self._feeds.keys()))
        raise KeyError(
            f"Unknown feed '{name_or_uri}'. "
            f"Available names: {available}. "
            f"Or pass a raw AT URI starting with 'at://'."
        )

    def _tree_is_truncated(
        self,
        node: models.AppBskyFeedDefs.ThreadViewPost,
        _visited: Optional[set] = None,
    ) -> bool:
        """
        Recursively check whether any node in the thread tree has replies=None
        (truncated by depth limit) rather than replies=[] (genuinely no replies).
        """
        if _visited is None:
            _visited = set()
        node_id = getattr(node.post, "uri", id(node))
        if node_id in _visited:
            return False
        _visited.add(node_id)

        if node.replies is None:
            # None means "not fetched" — this node was truncated
            return True
        for reply in node.replies:
            if isinstance(reply, models.AppBskyFeedDefs.ThreadViewPost):
                if self._tree_is_truncated(reply, _visited):
                    return True
        return False