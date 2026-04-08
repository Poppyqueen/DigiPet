"""
bluesky_client/client.py

Thin authenticated wrapper around the atproto Client.
BlueskyTools owns one instance of this as self.client.

Exposes:
    self.raw      — the underlying atproto Client for direct API calls
    self.handle   — bot handle string (from env)
    self.did      — resolved after login
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from atproto import Client
from atproto_client import Session, SessionEvent

from .helpers.feed import FeedHelper
from .helpers.notifications import NotificationHelper
from .helpers.posting import PostingHelper
from .helpers.images import ImageHelper

load_dotenv()
logger = logging.getLogger(__name__)

SESSION_FILE = Path("bluesky_session.txt")


class BskyBotClient:
    def __init__(self) -> None:
        self.handle: str = os.getenv("BLUESKY_HANDLE", "")
        password:    str = os.getenv("BLUESKY_PASSWORD", "")

        if not self.handle or not password:
            raise EnvironmentError(
                "BLUESKY_HANDLE and BLUESKY_PASSWORD must be set in environment / .env"
            )

        self.raw = Client()
        self.raw.on_session_change(self._on_session_change)
        self.did: Optional[str] = None

 
        # Modular helpers — all share a reference to this client so they can
        # read/write _eligible_dids and call the underlying atproto Client.
        self.notifications = NotificationHelper(self)
        self.posting = PostingHelper(self)
        self.feed = FeedHelper(self)
        self.images = ImageHelper(self)

        # Try cached session first to avoid login rate-limit hits
        session_str = self._load_session()
        if session_str:
            try:
                self.raw.login(session_string=session_str)
                logger.info("Resumed cached Bluesky session.")
            except Exception:
                logger.warning("Cached session invalid — falling back to password login.")
                self.raw.login(self.handle, password)
        else:
            self.raw.login(self.handle, password)

        self.did = self.raw.me.did
        logger.info("Logged in as %s (%s)", self.handle, self.did)

    def get_current_time_iso(self) -> str:
        return self.raw.get_current_time_iso()

    def _on_session_change(self, event: SessionEvent, session: Session) -> None:
        if event in (SessionEvent.CREATE, SessionEvent.REFRESH):
            SESSION_FILE.write_text(session.export(), encoding="utf-8")
            logger.debug("Session persisted (%s).", event)

    def _load_session(self) -> Optional[str]:
        try:
            return SESSION_FILE.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None