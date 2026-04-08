"""
discogs_tools.py

A clean, API-efficient toolkit for interacting with Discogs, designed for use by AI/LLMs.

Key design principles:
  - Server-side pagination: ask the API for only the page you need, never fetch everything.
  - No N+1 calls: use .data dict on artist releases to filter types without extra requests.
  - Adaptive rate limiting: read X-Discogs-Ratelimit-Used headers, sleep only when needed.
  - Simple instance-level cache: avoids the lru_cache-on-instance-method pitfall.
  - Exponential backoff: only on actual 429/5xx responses, not on every successful call.

Requirements:
  pip install python3-discogs-client python-dotenv

Environment variables (in a .env file or your shell):
  DISCOGS_USER_TOKEN   — your personal Discogs user token
  DISCOGS_AGENT_NAME   — your app's user-agent string, e.g. "MyApp/1.0"
"""

import os
import time

import discogs_client
from discogs_client.exceptions import HTTPError
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RATE_LIMIT_THRESHOLD = 0.85   # Sleep when used/total >= this fraction
_RATE_LIMIT_SLEEP     = 1.0    # Seconds to sleep when approaching the limit
_MAX_RETRY_ATTEMPTS   = 5
_BASE_BACKOFF_SECONDS = 2


# ---------------------------------------------------------------------------
# DiscogsTools
# ---------------------------------------------------------------------------

class DiscogsTools:
    """
    A collection of tools for interacting with the Discogs API.
    Manages its own authentication and provides single-purpose functions
    with clear natural-language outputs suitable for LLM consumption.
    """

    def __init__(self):
        """
        Load environment variables, authenticate with Discogs, and prepare
        an empty instance-level cache.

        Raises:
            RuntimeError: If authentication fails.
        """
        load_dotenv()

        agent = os.environ.get("DISCOGS_AGENT_NAME")
        token = os.environ.get("DISCOGS_USER_TOKEN")

        if not agent or not token:
            raise RuntimeError(
                "DISCOGS_AGENT_NAME and DISCOGS_USER_TOKEN must be set "
                "in your environment or .env file."
            )

        print("Initializing DiscogsTools...")
        self._client = discogs_client.Client(agent, user_token=token)
        self._me = self._call(self._client.identity, "identity verification")
        print(f"Authenticated as: {self._me.name} (ID: {self._me.id})")

        # Simple dict cache: key → result. Avoids lru_cache-on-self issues.
        self._cache: dict = {}

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _call(self, func, operation: str = "API call"):
        """
        Execute a callable with retry + exponential backoff on 429 / 5xx.
        Reads Discogs rate-limit headers and sleeps adaptively.

        Args:
            func:       A zero-argument callable that performs the API call.
            operation:  Human-readable name for log messages.

        Returns:
            Whatever func() returns.

        Raises:
            Exception on non-retryable errors or exhausted retries.
        """
        for attempt in range(_MAX_RETRY_ATTEMPTS):
            try:
                result = func()
                self._maybe_throttle()
                return result

            except HTTPError as exc:
                if exc.status_code == 429 or exc.status_code >= 500:
                    wait = _BASE_BACKOFF_SECONDS * (2 ** attempt) + (time.monotonic() % 1)
                    print(
                        f"[{exc.status_code}] {operation} — "
                        f"retrying in {wait:.1f}s (attempt {attempt + 1}/{_MAX_RETRY_ATTEMPTS})"
                    )
                    time.sleep(wait)
                else:
                    # 4xx that isn't 429: not retryable
                    raise

        raise RuntimeError(
            f"'{operation}' failed after {_MAX_RETRY_ATTEMPTS} attempts."
        )

    def _maybe_throttle(self):
        """
        Inspect the last response's rate-limit headers and sleep if we are
        close to the per-minute ceiling.  Discogs sends:
          X-Discogs-Ratelimit       total allowed requests in the window
          X-Discogs-Ratelimit-Used  how many we have used so far
        """
        try:
            headers  = self._client._fetcher.session.headers  # underlying requests.Session
            last_resp = getattr(self._client._fetcher, '_last_response', None)
            if last_resp is None:
                return
            total = int(last_resp.headers.get("X-Discogs-Ratelimit", 60))
            used  = int(last_resp.headers.get("X-Discogs-Ratelimit-Used", 0))
            if total > 0 and (used / total) >= _RATE_LIMIT_THRESHOLD:
                print(f"[rate-limit] {used}/{total} used — sleeping {_RATE_LIMIT_SLEEP}s")
                time.sleep(_RATE_LIMIT_SLEEP)
        except Exception:
            pass  # Header inspection is best-effort; never crash here

    def _cached(self, key, func):
        """Return a cached value, computing it via func() on first access."""
        if key not in self._cache:
            self._cache[key] = func()
        return self._cache[key]

    @staticmethod
    def _validate(**kwargs):
        """
        Lightweight argument validator.  Each kwarg is:
            name = (value, type, min=None, max=None, allow_none=False)

        Returns an error string on the first failure, or None if all pass.
        """
        for name, spec in kwargs.items():
            value, expected_type = spec[0], spec[1]
            min_val    = spec[2] if len(spec) > 2 else None
            max_val    = spec[3] if len(spec) > 3 else None
            allow_none = spec[4] if len(spec) > 4 else False

            if value is None:
                if not allow_none:
                    return f"Error: '{name}' cannot be None."
                continue
            if not isinstance(value, expected_type):
                return (
                    f"Error: '{name}' must be {expected_type.__name__}, "
                    f"got {type(value).__name__}."
                )
            if expected_type is str and not value.strip():
                return f"Error: '{name}' cannot be an empty string."
            if expected_type is int:
                if min_val is not None and value < min_val:
                    return f"Error: '{name}' must be ≥ {min_val}."
                if max_val is not None and value > max_val:
                    return f"Error: '{name}' must be ≤ {max_val}."
        return None

    # -----------------------------------------------------------------------
    # Cached object fetchers  (no network hit after first call per ID)
    # -----------------------------------------------------------------------

    def _get_artist(self, artist_id: int) -> discogs_client.models.Artist:
        return self._cached(
            f"artist:{artist_id}",
            lambda: self._call(
                lambda: self._client.artist(artist_id),
                f"fetch artist {artist_id}"
            )
        )

    def _get_master(self, master_id: int) -> discogs_client.models.Master:
        return self._cached(
            f"master:{master_id}",
            lambda: self._call(
                lambda: self._client.master(master_id),
                f"fetch master {master_id}"
            )
        )

    # -----------------------------------------------------------------------
    # Collection
    # -----------------------------------------------------------------------

    def get_collection_summary(self, page: int = 1, per_page: int = 25) -> str:
        """
        Return a summary of the user's collection for one page.

        Uses server-side pagination — only one API call per invocation.

        Args:
            page:     1-indexed page number.
            per_page: Items per page (1–100).

        Returns:
            Natural-language string, e.g.:
            "You have 312 items in your collection (page 1 of 13, 25 shown):
             - 'Music Has the Right to Children' by Boards of Canada
               Genres: Electronic  Styles: Ambient, IDM"
        """
        err = self._validate(
            page     = (page,     int, 1),
            per_page = (per_page, int, 1, 100),
        )
        if err:
            return err

        try:
            folder = self._call(
                lambda: self._me.collection_folders[0],
                "fetch collection folder"
            )

            # Ask the server for exactly the page we need.
            # PaginatedList.page(n) fires one request and returns that page's items.
            
            # Set the per_page property on the PaginatedList object first
            folder.releases.per_page = per_page
            
            # Then request the specific page
            paginated = folder.releases.page(page)
            total_items = folder.releases.count
            total_pages = (total_items + per_page - 1) // per_page

            if total_items == 0:
                return "Your Discogs collection is empty."
            if page > total_pages:
                return (
                    f"Page {page} is out of range. "
                    f"Your collection has {total_pages} page(s) ({total_items} items total)."
                )

            lines = []
            for item in paginated:
                r       = item.release
                artists = ", ".join(a.name for a in r.artists) if r.artists else "N/A"
                genres  = ", ".join(r.genres)  if r.genres  else "N/A"
                styles  = ", ".join(r.styles)  if r.styles  else "N/A"
                lines.append(
                    f"- '{r.title}' by {artists}\n"
                    f"  Genres: {genres}  Styles: {styles}"
                )

            header = (
                f"You have {total_items} items in your collection "
                f"(page {page} of {total_pages}, {len(lines)} shown):"
            )
            return header + "\n" + "\n".join(lines)

        except HTTPError as exc:
            if exc.status_code == 404:
                return "Collection not found. Make sure your account is accessible."
            return f"Failed to retrieve collection summary: HTTP {exc.status_code}."
        except Exception as exc:
            return f"Failed to retrieve collection summary: {exc}"

    def get_collection_unique_artists(self) -> str:
        """
        Return a sorted, deduplicated list of artist names in the user's collection.

        This walks all pages of the collection folder — unavoidable for a complete
        unique-artist list — but caches the result so subsequent calls are instant.

        Returns:
            "Found 47 unique artists in your collection: Artist A, Artist B, ..."
        """
        try:
            artists = self._cached(
                "collection_unique_artists",
                lambda: self._build_collection_artist_set()
            )
            if not artists:
                return "No artists found in your collection."
            sorted_artists = sorted(artists)
            return (
                f"Found {len(sorted_artists)} unique artists in your collection: "
                + ", ".join(sorted_artists)
            )
        except Exception as exc:
            return f"Failed to retrieve collection artists: {exc}"

    def _build_collection_artist_set(self) -> set:
        """Walk all collection pages and collect artist names. Cached by caller."""
        folder  = self._call(lambda: self._me.collection_folders[0], "fetch folder")
        artists = set()
        for item in folder.releases:          # PaginatedList: fetches pages lazily
            for artist in item.release.artists:
                artists.add(artist.name)
            self._maybe_throttle()
        return artists

    # -----------------------------------------------------------------------
    # Wantlist
    # -----------------------------------------------------------------------

    def get_wantlist_summary(self, page: int = 1, per_page: int = 25) -> str:
        """
        Return a summary of the user's wantlist for one page.

        Uses server-side pagination — only one API call per invocation.

        Args:
            page:     1-indexed page number.
            per_page: Items per page (1–100).

        Returns:
            Natural-language string, e.g.:
            "You have 58 items in your wantlist (page 1 of 3, 25 shown):
             - 'Geogaddi' by Boards of Canada
               Genres: Electronic  Styles: Ambient, IDM"
        """
        err = self._validate(
            page     = (page,     int, 1),
            per_page = (per_page, int, 1, 100),
        )
        if err:
            return err

        try:
            wantlist    = self._me.wantlist
            wantlist.per_page = per_page   # <--- Add this line

            total_items = wantlist.count
            total_pages = max(1, (total_items + per_page - 1) // per_page)

            if total_items == 0:
                return "Your Discogs wantlist is empty."
            if page > total_pages:
                return (
                    f"Page {page} is out of range. "
                    f"Your wantlist has {total_pages} page(s) ({total_items} items total)."
                )

            paginated = self._call(
                lambda: wantlist.page(page),
                f"fetch wantlist page {page}"
            )

            lines = []
            for item in paginated:
                r       = item.release
                artists = ", ".join(a.name for a in r.artists) if r.artists else "N/A"
                genres  = ", ".join(r.genres)  if r.genres  else "N/A"
                styles  = ", ".join(r.styles)  if r.styles  else "N/A"
                lines.append(
                    f"- '{r.title}' by {artists}\n"
                    f"  Genres: {genres}  Styles: {styles}"
                )

            header = (
                f"You have {total_items} items in your wantlist "
                f"(page {page} of {total_pages}, {len(lines)} shown):"
            )
            return header + "\n" + "\n".join(lines)

        except HTTPError as exc:
            return f"Failed to retrieve wantlist: HTTP {exc.status_code}."
        except Exception as exc:
            return f"Failed to retrieve wantlist: {exc}"

    def get_wantlist_unique_artists(self) -> str:
        """
        Return a sorted, deduplicated list of artist names in the user's wantlist.

        Result is cached after the first call.

        Returns:
            "Found 23 unique artists in your wantlist: Artist A, Artist B, ..."
        """
        try:
            artists = self._cached(
                "wantlist_unique_artists",
                lambda: self._build_wantlist_artist_set()
            )
            if not artists:
                return "No artists found in your wantlist."
            sorted_artists = sorted(artists)
            return (
                f"Found {len(sorted_artists)} unique artists in your wantlist: "
                + ", ".join(sorted_artists)
            )
        except Exception as exc:
            return f"Failed to retrieve wantlist artists: {exc}"

    def _build_wantlist_artist_set(self) -> set:
        """Walk all wantlist pages and collect artist names. Cached by caller."""
        artists = set()
        for item in self._me.wantlist:
            if hasattr(item.release, "artists"):
                for artist in item.release.artists:
                    artists.add(artist.name)
            self._maybe_throttle()
        return artists

    # -----------------------------------------------------------------------
    # Artist search & discography
    # -----------------------------------------------------------------------

    def search_artist_by_name(self, artist_name: str) -> str:
        """
        Search Discogs for an artist by name.  Prefers exact matches.

        Args:
            artist_name: Full or partial artist name.

        Returns:
            "Found artist 'Boards of Canada' (ID: 18456).
             Profile: ...
             URL: https://www.discogs.com/artist/18456"
            or "Artist 'X' not found on Discogs."
        """
        err = self._validate(artist_name=(artist_name, str))
        if err:
            return err

        try:
            results = self._call(
                lambda: self._client.search(artist_name, type="artist"),
                f"search artist '{artist_name}'"
            )

            best = None
            for res in results:
                if not isinstance(res, discogs_client.models.Artist):
                    continue
                if res.name.lower() == artist_name.lower():
                    best = res
                    break
                if best is None:
                    best = res   # fall back to first artist result

            if best is None:
                return f"Artist '{artist_name}' not found on Discogs."

            # Cache for downstream calls
            self._cache[f"artist:{best.id}"] = best

            profile = (best.profile or "No profile available.").strip()
            return (
                f"Found artist '{best.name}' (ID: {best.id}).\n"
                f"Profile: {profile}\n"
                f"URL: {best.url}"
            )

        except Exception as exc:
            return f"Failed to search for artist '{artist_name}': {exc}"

    def get_artist_discography(
        self,
        artist_id: int,
        page: int = 1,
        per_page: int = 10,
        only_main: bool = True,
    ) -> str:
        """
        List master releases for an artist, using server-side pagination.

        No N+1 problem: we check release type and role directly from the .data
        dict returned by the /artists/{id}/releases endpoint, which already
        contains {'type': 'master', 'role': 'Main'} — without fetching each
        master's main_release separately.

        Args:
            artist_id: Discogs artist ID.
            page:      1-indexed page of results.
            per_page:  Items per page (1–100).
            only_main: If True (default), skip releases where the artist is
                       credited as a guest/feature/remix rather than main artist.

        Returns:
            "Discography for 'Boards of Canada' — 8 master releases (page 1 of 1):
             1. 'Music Has the Right to Children' (1998) — Master ID: 43396
             2. 'Geogaddi' (2002) — Master ID: 56621
             ..."
        """
        err = self._validate(
            artist_id = (artist_id, int, 1),
            page      = (page,      int, 1),
            per_page  = (per_page,  int, 1, 100),
        )
        if err:
            return err

        try:
            artist          = self._get_artist(artist_id)
            releases_list   = artist.releases
            releases_list.per_page = per_page  # <--- Add this line


            # Server-side: request the specific page.
            # The /artists/{id}/releases endpoint returns a mix of masters,
            # singles, appearances etc., so we filter by .data after fetching.
            page_items = self._call(
                lambda: releases_list.page(page),
                f"fetch releases page {page} for artist {artist_id}"
            )
            total_items = releases_list.count
            total_pages = max(1, (total_items + per_page - 1) // per_page)

            if total_items == 0:
                return f"No releases found for artist '{artist.name}' (ID: {artist_id})."

            masters = []
            for rel in page_items:
                d = rel.data
                if d.get("type") != "master":
                    continue
                if only_main and d.get("role", "").lower() != "main":
                    continue
                masters.append(rel)

            if not masters:
                return (
                    f"No main master releases on page {page} for '{artist.name}'. "
                    f"Try a different page (total pages: {total_pages}) or set only_main=False."
                )

            lines = []
            for i, rel in enumerate(masters, start=1):
                year  = f" ({rel.data.get('year', '?')})" if rel.data.get("year") else ""
                lines.append(f"{i}. '{rel.title}'{year} — Master ID: {rel.id}")

            header = (
                f"Discography for '{artist.name}' — showing {len(masters)} master(s) "
                f"from page {page}/{total_pages} (page contains {len(page_items)} total releases, "
                f"filtered to main masters):"
            )
            return header + "\n" + "\n".join(lines)

        except HTTPError as exc:
            if exc.status_code == 404:
                return f"Artist ID {artist_id} not found on Discogs."
            return f"Failed to fetch discography for artist {artist_id}: HTTP {exc.status_code}."
        except Exception as exc:
            return f"Failed to fetch discography for artist {artist_id}: {exc}"

    # -----------------------------------------------------------------------
    # Master release search & details
    # -----------------------------------------------------------------------

    def search_master_by_title(
        self,
        title: str,
        artist_name: str = None,
        limit: int = 5,
    ) -> str:
        """
        Search for master releases by title (and optionally artist name).

        Args:
            title:       Release title to search for.
            artist_name: Optional artist name to narrow results.
            limit:       Max results to return (1–10).

        Returns:
            "Found 3 master releases for 'The Wall':
             1. 'The Wall' by Pink Floyd — Master ID: 406969
             2. ..."
        """
        err = self._validate(
            title       = (title,       str),
            artist_name = (artist_name, str, None, None, True),
            limit       = (limit,       int, 1, 10),
        )
        if err:
            return err

        query = f"{title} {artist_name}".strip() if artist_name else title

        try:
            results = self._call(
                lambda: self._client.search(query, type="master"),
                f"search master '{query}'"
            )

            found = []
            for item in results:
                if len(found) >= limit:
                    break
                found.append(item)

            if not found:
                return f"No master releases found matching '{query}'."

            lines = []
            for i, master in enumerate(found, start=1):
                # Artists are available from .data without an extra API call.
                artists = "Unknown Artist"
                if master.data.get("artists"):
                    artists = ", ".join(a["name"] for a in master.data["artists"])
                lines.append(f"{i}. '{master.title}' by {artists} — Master ID: {master.id}")

            return f"Found {len(found)} master release(s) for '{query}':\n" + "\n".join(lines)

        except Exception as exc:
            return f"Failed to search for master '{query}': {exc}"

    def get_master_tracklist(self, master_id: int, include_videos: bool = True) -> str:
        """
        Return the tracklist (and optionally YouTube links) for a master release.

        Args:
            master_id:      Discogs Master ID.
            include_videos: If True, append YouTube/video links stored in Discogs.

        Returns:
            "Tracklist for 'Music Has the Right to Children' (Master ID: 43396)
             Genres: Electronic  Styles: Ambient, IDM
             A1. Wildlife Analysis (2:27)
             A2. An Eagle in Your Mind (7:02)
             ..."
        """
        err = self._validate(master_id=(master_id, int, 1))
        if err:
            return err

        try:
            master = self._get_master(master_id)

            genres = ", ".join(master.genres) if master.genres else "N/A"
            styles = ", ".join(master.styles) if master.styles else "N/A"

            if not master.tracklist:
                return (
                    f"No tracklist found for '{getattr(master, 'title', '?')}' "
                    f"(Master ID: {master_id})."
                )

            lines = [
                f"Tracklist for '{master.title}' (Master ID: {master.id})",
                f"Genres: {genres}  Styles: {styles}",
                "",
            ]
            for track in master.tracklist:
                pos      = getattr(track, "position", "") or ""
                title    = getattr(track, "title",    "Unknown Track")
                duration = (getattr(track, "duration", "") or "").strip()
                dur_str  = f" ({duration})" if duration else ""
                lines.append(f"{pos}. {title}{dur_str}" if pos else f"  {title}{dur_str}")

            if include_videos:
                if not getattr(master, "videos", None):
                    lines.append("\nNo video links found for this release.")
                else:
                    lines.append("\nVideo links:")
                    for video in master.videos:
                        v_title = getattr(video, "title", "No title")
                        uri     = (
                            video.data.get("uri")
                            if hasattr(video, "data") and video.data
                            else "No link"
                        )
                        lines.append(f"  - {v_title}: {uri}")

            return "\n".join(lines)

        except HTTPError as exc:
            if exc.status_code == 404:
                return f"Master release ID {master_id} not found on Discogs."
            return f"Failed to retrieve tracklist for Master ID {master_id}: HTTP {exc.status_code}."
        except Exception as exc:
            return f"Failed to retrieve tracklist for Master ID {master_id}: {exc}"


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        tools = DiscogsTools()
        print("\n=== Collection (page 1, 5 items) ===")
        print(tools.get_collection_summary(page=1, per_page=5))

        print("\n=== Wantlist (page 1, 5 items) ===")
        print(tools.get_wantlist_summary(page=1, per_page=5))

        print("\n=== Search artist ===")
        result = tools.search_artist_by_name("Boards of Canada")
        print(result)

        if "ID:" in result:
            artist_id = int(result.split("ID: ")[1].split(")")[0].strip())

            print(f"\n=== Discography for artist {artist_id} (page 1) ===")
            print(tools.get_artist_discography(artist_id, page=1, per_page=20))

        print("\n=== Search master ===")
        masters = tools.search_master_by_title("Music Has the Right to Children", "Boards of Canada")
        print(masters)

        if "Master ID:" in masters:
            master_id = int(masters.split("Master ID: ")[1].split("\n")[0].strip())
            print(f"\n=== Tracklist for master {master_id} ===")
            print(tools.get_master_tracklist(master_id, include_videos=True))

    except Exception as e:
        print(f"\nInitialization failed: {e}")