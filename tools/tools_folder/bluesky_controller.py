"""
bluesky_client/controller.py

LLM tool interface. One class: BlueskyTools.
Owns self.client (BskyBotClient) directly.
All helpers live in helpers/ unchanged.

_validate_interface(item_id) checks: is the player near a Bluesky terminal?
The item is a physical prop in the game world — carries no credentials.

Every public method returns:
    {"ok": True,  "data": {...}}
 or {"ok": False, "error": "..."}
"""
# Thanks to the Bluesky team and the Atproto Python client library, which made this integration possible.
# All code for this integration was derived from these examples: https://github.com/MarshalX/atproto/tree/main/examples

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from tools.tools_folder.tools_helpers.bluesky_bot.client import BskyBotClient
from tools.tools_folder.tools_helpers.bluesky_bot.helpers.posting import _post_mentions_us
from tools.tools_folder.tools_helpers.svg_manager import SVGManager



if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

logger = logging.getLogger(__name__)

BLUESKY_ACCESS_TYPE = "bluesky_social_endpoint"


def _ok(data):  return {"ok": True,  "data": data}
def _err(msg):  return {"ok": False, "error": msg}
def _paging(pg): return pg.summary()


def _ser_post(pv):
    r, a = pv.record, pv.author
    return {
        "uri": pv.uri, "cid": pv.cid,
        "text": getattr(r, "text", ""),
        "created_at": getattr(r, "created_at", None),
        "author": {"did": a.did, "handle": a.handle,
                   "display_name": getattr(a, "display_name", None)},
        "like_count":   getattr(pv, "like_count",   0) or 0,
        "reply_count":  getattr(pv, "reply_count",  0) or 0,
        "repost_count": getattr(pv, "repost_count", 0) or 0,
    }

def _ser_feed_item(fv): return _ser_post(fv.post)

def _ser_notification(n):
    d = {
        "uri": n.uri, "cid": n.cid, "reason": n.reason,
        "is_read": n.is_read, "indexed_at": n.indexed_at,
        "author": {"did": n.author.did, "handle": n.author.handle,
                   "display_name": getattr(n.author, "display_name", None)},
    }
    if hasattr(n, "record") and n.record:
        d["text"] = getattr(n.record, "text", None)
    return d

def _ser_thread_reply(node_tuple):
    # Unpack the tuple provided by the updated get_thread
    node, depth = node_tuple 
    pv = node.post
    return {
        "uri": pv.uri, "cid": pv.cid,
        "text": getattr(pv.record, "text", ""),
        "created_at": getattr(pv.record, "created_at", None),
        "author": {"did": pv.author.did, "handle": pv.author.handle},
        "reply_count": getattr(pv, "reply_count", 0) or 0,
        "has_deeper_replies": node.replies is None or bool(node.replies),
        "depth": depth,  # <--- CRUCIAL: tells the LLM the nesting level structurally
    }


class BlueskyTools:
    """
    All Bluesky tools for the LLM agent.

    Notifications : get_notifications, mark_notifications_seen
    Feed          : list_feeds, get_timeline, get_feed,
                    get_author_posts, get_thread
    Account       : get_account_summary, get_posts_needing_responses
    Posting       : post, post_with_image, respond_to_post,
                    update_profile_description
    """

    def __init__(self, state_manager: "InventoryHouseManager", signal, images_lab=None) -> None:
        self.state_manager = state_manager
        self._signal_callback = signal
        self.images_lab = images_lab

        self.svg_manager=SVGManager()

        print(f"We are on bluesky tools before client ...")

        self.client        = BskyBotClient()

        print(f"We are on bluesky tools after client ...")



    def _validate_interface(self, item_id: int):
        result = self.state_manager.find_item(
            item_id,
            required_type=BLUESKY_ACCESS_TYPE,
            required_location="accessible",
        )
        if not result.success:
            return None, result.error
        return result.item_data, None

    # ------------------------------------------------------------------ NOTIFICATIONS

    def get_notifications(self, item_id: int, unread_only: bool = True,
                          limit: int = 10, cursor: Optional[str] = None,
                          page: int = 1) -> Dict[str, Any]:
        """
        Fetch the bot's notifications. Does NOT mark them seen.
        Call mark_notifications_seen() after processing.

        Args:
            item_id:     Bluesky terminal item ID.
            unread_only: Only unread (default True).
            limit:       Per page, max 100.
            cursor:      From previous response for next page.
            page:        Page number for tracking.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            pg = (self.client.notifications.list_unread(limit=limit, cursor=cursor, page=page)
                  if unread_only else
                  self.client.notifications.list_all(limit=limit, cursor=cursor, page=page))
            summary = {}
            for n in pg.items:
                summary[n.reason] = summary.get(n.reason, 0) + 1
            return _ok({"notifications": [_ser_notification(n) for n in pg.items],
                        "summary": summary, "pagination": _paging(pg)})
        except Exception as exc:
            logger.exception("get_notifications failed")
            return _err(str(exc))

    def mark_notifications_seen(self, item_id: int,
                                 seen_at: Optional[str] = None) -> Dict[str, Any]:
        """
        Advance the server seen cursor. Best practice: capture seen_at BEFORE
        calling get_notifications(), pass it here AFTER processing.

        Args:
            item_id: Bluesky terminal item ID.
            seen_at: ISO timestamp (defaults to now).
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            ts = self.client.notifications.mark_seen(seen_at)
            return _ok({"marked_seen_at": ts})
        except Exception as exc:
            logger.exception("mark_notifications_seen failed")
            return _err(str(exc))

    # ------------------------------------------------------------------ FEED

    def list_feeds(self, item_id: int) -> Dict[str, Any]:
        """
        Return the registry of named feeds. Call before get_feed() to see valid names.

        Args:
            item_id: Bluesky terminal item ID.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        feeds_keys = list(self.client.feed.list_feeds().keys())
        return _ok({"feeds": feeds_keys})

    def get_timeline(self, item_id: int, limit: int = 10,
                     cursor: Optional[str] = None, page: int = 1) -> Dict[str, Any]:
        """
        Fetch the bot's home timeline (accounts it follows).

        Args:
            item_id: Bluesky terminal item ID.
            limit:   Per page, max 100.
            cursor:  From previous response for next page.
            page:    Page number for tracking.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            pg = self.client.feed.get_timeline(limit=limit, cursor=cursor, page=page)
            return _ok({"posts": [_ser_feed_item(p) for p in pg.items], "pagination": _paging(pg)})
        except Exception as exc:
            logger.exception("get_timeline failed")
            return _err(str(exc))

    def get_feed(self, item_id: int, name_or_uri: str = "whats-hot",
                 limit: int = 10, cursor: Optional[str] = None,
                 page: int = 1) -> Dict[str, Any]:
        """
        Fetch posts from a named feed or raw AT URI.

        Args:
            item_id:     Bluesky terminal item ID.
            name_or_uri: Name from list_feeds() or a raw 'at://' URI.
            limit:       Per page.
            cursor:      From previous response for next page.
            page:        Page number for tracking.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            pg = self.client.feed.get_feed(name_or_uri=name_or_uri,
                                           limit=limit, cursor=cursor, page=page)
            return _ok({"feed": name_or_uri,
                        "posts": [_ser_feed_item(p) for p in pg.items],
                        "pagination": _paging(pg)})
        except KeyError as exc:
            return _err(str(exc))
        except Exception as exc:
            logger.exception("get_feed failed")
            return _err(str(exc))

    def get_author_posts(self, item_id: int, actor: str, limit: int = 10,
                         cursor: Optional[str] = None, page: int = 1) -> Dict[str, Any]:
        """
        Fetch posts from a specific author.

        Args:
            item_id: Bluesky terminal item ID.
            actor:   Handle or DID.
            limit:   Per page.
            cursor:  From previous response for next page.
            page:    Page number for tracking.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            pg = self.client.feed.get_author_posts(actor=actor, limit=limit,
                                                   cursor=cursor, page=page)
            return _ok({"actor": actor,
                        "posts": [_ser_feed_item(p) for p in pg.items],
                        "pagination": _paging(pg)})
        except Exception as exc:
            logger.exception("get_author_posts failed")
            return _err(str(exc))

    def get_thread(self, item_id: int, uri: str, limit: int = 10, page: int = 1) -> Dict[str, Any]:
        """
        Fetch a post thread. Increment page to load more replies sequentially.
        """
        limit = min(limit, 15) # Hard cap limit
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            pg = self.client.feed.get_thread(uri=uri, limit=limit, page=page)
            return _ok({"root_uri": uri,
                        "replies": [_ser_thread_reply(r) for r in pg.items],
                        "pagination": _paging(pg)})
        except Exception as exc:
            logger.exception("get_thread failed")
            return _err(str(exc))

    # ------------------------------------------------------------------ ACCOUNT

    def get_account_summary(self, item_id: int, limit: int = 10) -> Dict[str, Any]:
        """
        Return the bot's own profile and recent posts with engagement stats.

        Args:
            item_id: Bluesky terminal item ID.
            limit:   Number of recent posts to include.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            profile = self.client.raw.get_profile(self.client.raw.me.handle)
            feed    = self.client.raw.get_author_feed(actor=self.client.raw.me.did, limit=limit)
            own_posts = [_ser_post(p.post) for p in feed.feed
                         if p.post.author.did == self.client.raw.me.did]
            return _ok({
                "profile": {
                    "handle": profile.handle, "display_name": profile.display_name,
                    "description": profile.description,
                    "followers_count": profile.followers_count,
                    "follows_count": profile.follows_count,
                    "posts_count": profile.posts_count,
                },
                "recent_posts": own_posts,
            })
        except Exception as exc:
            logger.exception("get_account_summary failed")
            return _err(str(exc))

    def get_posts_needing_responses(self, item_id: int,
                                    limit: int = 10) -> Dict[str, Any]:
        """
        Return our own posts whose threads contain replies that @-mention the bot,
        where the bot has not yet replied last.

        The agent should call respond_to_post() on URIs from the "mentions" list.

        Args:
            item_id: Bluesky terminal item ID.
            limit:   How many of our recent posts to scan.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)

        from atproto import models as _m

        our_did    = self.client.raw.me.did
        our_handle = self.client.handle

        def _collect(node, depth=0, max_depth=5):
            out = []
            if depth > max_depth:
                return out
            for reply in getattr(node, "replies", None) or []:
                if not isinstance(reply, _m.AppBskyFeedDefs.ThreadViewPost):
                    continue
                pv = reply.post
                out.append({
                    "uri":          pv.uri,
                    "cid":          pv.cid,
                    "author":       pv.author.handle,
                    "text":         getattr(pv.record, "text", ""),
                    "created_at":   getattr(pv.record, "created_at", None),
                    "depth":        depth,
                    "mentions_us":  _post_mentions_us(pv.record, our_did, our_handle),
                    "is_our_reply": pv.author.did == our_did,
                })
                out.extend(_collect(reply, depth + 1, max_depth))
            return out

        try:
            feed = self.client.raw.get_author_feed(actor=our_did, limit=limit)
        except Exception as exc:
            return _err(f"Could not fetch own posts: {exc}")

        needs_response = []
        for item in feed.feed:
            post = item.post
            if post.author.did != our_did or not (post.reply_count or 0):
                continue
            try:
                resp   = self.client.raw.app.bsky.feed.get_post_thread(
                    _m.AppBskyFeedGetPostThread.Params(uri=post.uri, depth=6))
                thread = resp.thread
                if not isinstance(thread, _m.AppBskyFeedDefs.ThreadViewPost):
                    continue
                replies      = _collect(thread)
                has_mention  = any(r["mentions_us"] for r in replies)
                last_is_ours = bool(replies) and replies[-1]["is_our_reply"]
                
                if has_mention and not last_is_ours:
                    # TOKEN BOMB PREVENTION: Truncate large context arrays
                    MAX_THREAD_CONTEXT = 15
                    MAX_MENTIONS_CONTEXT = 5
                    
                    mentions = [{"uri": r["uri"], "cid": r["cid"],
                                 "author": r["author"], "text": r["text"]}
                                for r in replies if r["mentions_us"]]

                    needs_response.append({
                        "original_post": _ser_post(post),
                        "thread": replies[-MAX_THREAD_CONTEXT:], # Take only the tail (latest context)
                        "mentions": mentions[:MAX_MENTIONS_CONTEXT],
                    })
            except Exception as exc:
                logger.warning("Could not fetch thread for %s: %s", post.uri, exc)

        needs_response = needs_response[:limit] # Enforce absolute limit
        return _ok({"posts_needing_response": needs_response,
                    "count": len(needs_response)})

    # ------------------------------------------------------------------ POSTING

    def post(self, item_id: int, text: str,
             langs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Publish a plain post. No mention check — we are initiating.

        Args:
            item_id: Bluesky terminal item ID.
            text:    Post text (max 300 graphemes).
            langs:   BCP-47 language tags e.g. ['en'].
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            ref = self.client.posting.post(text=text, langs=langs or ["en"])
            return _ok({"uri": ref.uri, "cid": ref.cid})
        except (ValueError, RuntimeError) as exc:
            return _err(str(exc))
        except Exception as exc:
            logger.exception("post failed")
            return _err(str(exc))

    def post_with_image(self, item_id: int, text: str, image_name: str,
                        image_alt: str, aspect_ratio_width: Optional[int] = None,
                        aspect_ratio_height: Optional[int] = None,
                        langs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Publish a post with a single image. No mention check — we are initiating.

        Args:
            item_id:             Bluesky terminal item ID.
            text:                Post text (max 300 graphemes).
            image_name:          Name of the image in an image book. (Special item interaction.)
            image_alt:           Alt text.
            aspect_ratio_width:  Optional width hint.
            aspect_ratio_height: Optional height hint.
            langs:               BCP-47 language tags.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        from atproto import models as _m
        aspect = None
        if aspect_ratio_width and aspect_ratio_height:
            aspect = _m.AppBskyEmbedDefs.AspectRatio(
                width=aspect_ratio_width, height=aspect_ratio_height)
            
        metadata=self.images_lab._int_get_arch()
            
        img_bytes, alt = self.svg_manager._prepare_image_data(metadata,image_name)
        if img_bytes is None:
            return f"Image Error: {alt}"  # Error message is returned in alt
        
        try:
            ref = self.client.posting.post_with_image(
                text=text, image_bytes=img_bytes,
                image_alt=image_alt, aspect_ratio=aspect)
            return _ok({"uri": ref.uri, "cid": ref.cid})
        except (ValueError, RuntimeError) as exc:
            return _err(str(exc))
        except Exception as exc:
            logger.exception("post_with_image failed")
            return _err(str(exc))

    def respond_to_post(self, item_id: int, uri: str, text: str,
                        langs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Reply to a post. Fetches the post and checks it @-mentions the bot first.
        Blocked if the post does not mention us.

        Args:
            item_id: Bluesky terminal item ID.
            uri:     AT URI of the post to reply to.
            text:    Reply text (max 300 graphemes).
            langs:   BCP-47 language tags.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            ref = self.client.posting.reply_to_post(
                uri=uri, text=text, langs=langs or ["en"])
            if ref is None:
                return _err(
                    "This post does not @-mention the bot. "
                    "Per Bluesky guidelines the bot may only reply to posts that tag it.")
            return _ok({"uri": ref.uri, "cid": ref.cid})
        except (ValueError, RuntimeError) as exc:
            return _err(str(exc))
        except Exception as exc:
            logger.exception("respond_to_post failed")
            return _err(str(exc))

    def update_profile_description(self, item_id: int,
                                    description: str) -> Dict[str, Any]:
        """
        Update the bot's profile bio.

        Args:
            item_id:     Bluesky terminal item ID.
            description: New bio text.
        """
        _, error = self._validate_interface(item_id)
        if error: return _err(error)
        try:
            from atproto import models as _m
            current = self.client.raw.app.bsky.actor.profile.get(
                self.client.raw.me.did, "self")
            p = current.value
            self.client.raw.com.atproto.repo.put_record(
                _m.ComAtprotoRepoPutRecord.Data(
                    collection=_m.ids.AppBskyActorProfile,
                    repo=self.client.raw.me.did, rkey="self",
                    swap_record=current.cid,
                    record=_m.AppBskyActorProfile.Record(
                        avatar=p.avatar, banner=p.banner,
                        description=description, display_name=p.display_name)))
            return _ok({"updated": True})
        except Exception as exc:
            logger.exception("update_profile_description failed")
            return _err(str(exc))