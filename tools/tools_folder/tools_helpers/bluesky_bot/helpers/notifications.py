"""
bluesky_client/helpers/notifications.py

Fetches notifications, marks them as seen, and — crucially — extracts the
set of DIDs that have @-mentioned the bot. Only those DIDs are added to the
eligibility gate; no other notification type unlocks interaction.

Notification reasons returned by the API:
    like               — someone liked our post
    repost             — someone reposted our post
    follow             — someone followed us
    mention            — someone @-mentioned us in a post  ← opt-in signal
    reply              — someone replied to our post       ← opt-in signal
    quote              — someone quoted our post
    starterpack-joined — someone joined via our starter pack

Pagination:
    The Bluesky notification API uses an opaque string cursor.
    All listing methods return Page[Notification] so the controller and LLM
    always see the same envelope shape.

mark_seen:
    The API only exposes a timestamp cursor — there is no per-notification ID
    to mark individually. The correct pattern is:

        seen_at = bot.get_current_time_iso()   # snapshot BEFORE fetching
        page = notifications.list_unread()
        ...process...
        notifications.mark_seen(seen_at)       # advance cursor to snapshot time

    Passing the pre-fetch timestamp ensures nothing that arrived during
    processing is accidentally swallowed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from atproto import models

from .pagination import Page

if TYPE_CHECKING:
    from ...bluesky_bot.client import BskyBotClient

logger = logging.getLogger(__name__)

_OPT_IN_REASONS = frozenset({"mention", "reply"})

Notification = models.AppBskyNotificationListNotifications.Notification

# Sensible default page size — large enough to catch a burst, small enough
# not to bloat LLM context on a busy account.
DEFAULT_LIMIT = 25


class NotificationHelper:
    """
    Notification fetching, eligibility extraction, and seen-cursor management.

    All list methods return Page[Notification]. The controller serialises items
    to dicts before passing to the LLM; helpers work with raw model objects.

    Typical controller loop:
        seen_at = bot.get_current_time_iso()
        page = bot.notifications.list_unread()
        # ... process page.items ...
        if page.has_more:
            page2 = bot.notifications.list_unread(cursor=page.cursor, page=2)
        bot.notifications.mark_seen(seen_at)
    """

    def __init__(self, bot: "BskyBotClient") -> None:
        self._bot = bot

    # ------------------------------------------------------------------
    # Public API — listing
    # ------------------------------------------------------------------

    def list_unread(
        self,
        limit: int = DEFAULT_LIMIT,
        cursor: Optional[str] = None,
        page: int = 1,
    ) -> Page[Notification]:
        """
        Return a page of UNREAD notifications.

        Args:
            limit:  Items per page (max 100).
            cursor: Opaque cursor from a previous Page.cursor to fetch next page.
            page:   Page number for tracking (caller-managed, passed through).

        Returns:
            Page[Notification] — check .has_more and .cursor for next page.
        """
        response = self._bot.raw.app.bsky.notification.list_notifications(
            params=models.AppBskyNotificationListNotifications.Params(
                limit=limit,
                cursor=cursor,
            )
        )
        unread = [n for n in response.notifications if not n.is_read]
        result = Page(
            items=unread,
            cursor=response.cursor,
            page=page,
        )
        logger.debug(
            "list_unread page=%d: %d unread of %d fetched, has_more=%s",
            page, len(unread), len(response.notifications), result.has_more,
        )
        return result

    def list_all(
        self,
        limit: int = DEFAULT_LIMIT,
        cursor: Optional[str] = None,
        page: int = 1,
    ) -> Page[Notification]:
        """
        Return a page of ALL notifications (read and unread).

        Args:
            limit:  Items per page (max 100).
            cursor: Opaque cursor from a previous Page.cursor.
            page:   Page number for tracking.

        Returns:
            Page[Notification].
        """
        response = self._bot.raw.app.bsky.notification.list_notifications(
            params=models.AppBskyNotificationListNotifications.Params(
                limit=limit,
                cursor=cursor,
            )
        )
        result = Page(
            items=list(response.notifications),
            cursor=response.cursor,
            page=page,
        )
        logger.debug(
            "list_all page=%d: %d items, has_more=%s",
            page, result.count, result.has_more,
        )
        return result

    # ------------------------------------------------------------------
    # Public API — seen cursor
    # ------------------------------------------------------------------

    def mark_seen(self, seen_at: Optional[str] = None) -> str:
        """
        Advance the server-side seen cursor.

        Args:
            seen_at: ISO timestamp string. If None, uses the current time.
                     Best practice: capture bot.get_current_time_iso() BEFORE
                     fetching notifications, then pass that value here AFTER
                     processing — this avoids swallowing notifications that
                     arrived during processing.

        Returns:
            The timestamp that was actually used (useful for logging).
        """
        ts = seen_at or self._bot.get_current_time_iso()
        self._bot.raw.app.bsky.notification.update_seen({"seen_at": ts})
        logger.debug("Notifications marked seen at %s.", ts)
        return ts

    # ------------------------------------------------------------------
    # Public API — eligibility
    # ------------------------------------------------------------------

    def get_eligible_dids(self, notifications: List[Notification]) -> set[str]:
        """
        Return the set of DIDs that opted in (mention/reply) from a list.
        Does NOT mutate the bot's eligibility gate — pure query.
        """
        return {n.author.did for n in notifications if n.reason in _OPT_IN_REASONS}

    def populate_gate(self, notifications: List[Notification]) -> int:
        """
        Add opt-in DIDs from a notification list to the bot's eligibility gate.

        Returns:
            Number of new DIDs added (0 if all were already eligible).
        """
        before = len(self._bot._eligible_dids)
        for n in notifications:
            if n.reason in _OPT_IN_REASONS:
                self._bot.add_eligible_did(n.author.did)
                logger.info("Gate: added %s (reason=%s)", n.author.did, n.reason)
        added = len(self._bot._eligible_dids) - before
        if added:
            logger.debug("Gate grew by %d DID(s).", added)
        return added

    def summarise(self, notifications: List[Notification]) -> dict[str, int]:
        """
        Count breakdown by reason — for logging and LLM context summaries.

        Example: {'like': 3, 'mention': 2, 'reply': 1}
        """
        summary: dict[str, int] = {}
        for n in notifications:
            summary[n.reason] = summary.get(n.reason, 0) + 1
        return summary

    # ------------------------------------------------------------------
    # Convenience: full single-sweep process (used by simple bot loops)
    # ------------------------------------------------------------------

    def process(self) -> Page[Notification]:
        """
        Snapshot time → fetch unread page 1 → populate gate → mark seen.

        For simple bots that don't need multi-page notification sweeps.
        For LLM controllers that may need to paginate, use list_unread()
        and mark_seen() separately.

        Returns:
            Page[Notification] of unread items (first page only).
        """
        seen_at = self._bot.get_current_time_iso()
        page = self.list_unread()
        self.populate_gate(page.items)
        self.mark_seen(seen_at)
        return page