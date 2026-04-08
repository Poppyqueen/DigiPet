"""
bluesky_client/helpers/posting.py

Outbound posting. One rule for replies:

    _post_mentions_us(post_record, our_did, our_handle)

    Fetched at reply-time on the specific post being replied to.
    Per Bluesky guidelines: only interact if that post tags the bot.
    No user history, no allowlist — per-post, every time.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional, Union

import grapheme
from atproto import models, client_utils, AtUri

if TYPE_CHECKING:
    from ...bluesky_bot.client import BskyBotClient

logger = logging.getLogger(__name__)

BLUESKY_CHAR_LIMIT = 300
TextInput = Union[str, client_utils.TextBuilder]
StrongRef = models.ComAtprotoRepoStrongRef.Main


def _make_ref(uri: str, cid: str) -> StrongRef:
    return StrongRef(uri=uri, cid=cid)


def _check_length(text: TextInput) -> tuple[bool, int]:
    """Return (within_limit, grapheme_count)."""
    raw = text.build_text() if isinstance(text, client_utils.TextBuilder) else str(text)
    count = grapheme.length(raw)
    return count <= BLUESKY_CHAR_LIMIT, count


def _post_mentions_us(post_record, our_did: str, our_handle: str) -> bool:
    """
    Return True if this specific post explicitly @-mentions the bot.

    Checks structured facets first (reliable), then falls back to plain
    text search. Called at reply-time on the exact post being replied to.
    """
    # Primary: structured facets
    for facet in getattr(post_record, "facets", None) or []:
        for feature in getattr(facet, "features", None) or []:
            if getattr(feature, "did", None) == our_did:
                return True
    # Fallback: text search
    return f"@{our_handle}".lower() in (getattr(post_record, "text", "") or "").lower()


class PostingHelper:
    def __init__(self, bot: "BskyBotClient") -> None:
        self._bot = bot

    def post(
        self,
        text: TextInput,
        embed=None,
        facets=None,
        langs=None,
    ):
        """Publish a plain post. No mention check — we are initiating."""
        ok, count = _check_length(text)
        if not ok:
            raise ValueError(f"Text is {count} graphemes — exceeds the {BLUESKY_CHAR_LIMIT} limit.")
        ref = self._bot.raw.send_post(text=text, embed=embed, facets=facets, langs=langs)
        logger.info("Posted: %s", ref.uri)
        return ref

    def reply_to_post(self, uri: str, text: TextInput, embed=None, langs=None):
        """
        Reply to a post at uri — only if that post @-mentions the bot.
        Returns None if the post does not mention us.
        """
        ok, count = _check_length(text)
        if not ok:
            raise ValueError(f"Text is {count} graphemes — exceeds the {BLUESKY_CHAR_LIMIT} limit.")

        our_did    = self._bot.raw.me.did
        our_handle = self._bot.handle

        try:
            at_uri = AtUri.from_str(uri)
            record_resp = self._bot.raw.com.atproto.repo.get_record(params={
                "repo":       at_uri.host,
                "collection": "app.bsky.feed.post",
                "rkey":       at_uri.rkey,
            })
        except Exception as exc:
            raise RuntimeError(f"Could not fetch post {uri}: {exc}") from exc

        if not _post_mentions_us(record_resp.value, our_did, our_handle):
            logger.warning("BLOCKED reply to %s — post does not mention us.", uri)
            return None

        parent_ref = _make_ref(str(record_resp.uri), str(record_resp.cid))
        root_ref   = parent_ref
        if record_resp.value and record_resp.value.reply and record_resp.value.reply.root:
            root_ref = record_resp.value.reply.root

        reply_ref = models.AppBskyFeedPost.ReplyRef(parent=parent_ref, root=root_ref)
        ref = self._bot.raw.send_post(text=text, reply_to=reply_ref, embed=embed, langs=langs)
        logger.info("Replied to %s → %s", uri, ref.uri)
        return ref

    def build_quote_embed(self, quoted_uri: str, quoted_cid: str):
        """
        Build a quote-post embed — only if the quoted post mentions the bot.
        Returns None if the post does not mention us.
        """
        try:
            at_uri = AtUri.from_str(quoted_uri)
            record_resp = self._bot.raw.com.atproto.repo.get_record(params={
                "repo":       at_uri.host,
                "collection": "app.bsky.feed.post",
                "rkey":       at_uri.rkey,
            })
        except Exception as exc:
            raise RuntimeError(f"Could not fetch post {quoted_uri}: {exc}") from exc

        if not _post_mentions_us(record_resp.value, self._bot.raw.me.did, self._bot.handle):
            logger.warning("BLOCKED quote of %s — post does not mention us.", quoted_uri)
            return None

        return models.AppBskyEmbedRecord.Main(record=_make_ref(quoted_uri, quoted_cid))

    def post_with_image(self, text: str, image_bytes: bytes, image_alt: str, aspect_ratio=None):
        """Post with a single image. No mention check — we are initiating."""
        embed = self._bot.images.build_image_embed([(image_bytes, image_alt, aspect_ratio)])
        return self.post(text=text, embed=embed)