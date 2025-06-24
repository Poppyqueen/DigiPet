import os
import time
import functools
from dotenv import load_dotenv
import discogs_client
from discogs_client.exceptions import HTTPError

# Make sure to set up your .env with DISCOGS_AGENT_NAME and DISCOGS_USER_TOKEN

# Pattern 1 & 2: Class Encapsulation & Self-Contained Authentication
class DiscogsTools:
    """
    A collection of tools for interacting with the Discogs API, designed for use by AI/LLMs.
    Manages its own authentication and provides granular, single-purpose functions
    with clear natural language outputs.
    """
    _RETRY_ATTEMPTS = 5
    _BASE_RETRY_DELAY_SECONDS = 2
    _CACHE_MAXSIZE = 128 # Max size for LRU cache for general-purpose functions
    _DATA_CACHE_MAXSIZE = 32 # A smaller cache for functions that store large data lists

    def __init__(self):
        """
        Initializes the DiscogsTools by loading environment variables and authenticating
        with the Discogs API.

        Raises:
            Exception: If authentication fails after multiple retries.
        """
        load_dotenv()  # Load environment variables from .env file
        self.user_agent = os.environ.get("DISCOGS_AGENT_NAME") # set your ID name for Discogs
        self.d_client = None
        self.me = None
        print("Initializing DiscogsTools...") # Pattern 7: Separate Internal Logging/Prints
        # Pattern 8: Robust Error Handling and Retries for authentication
        try:
            self.d_client = self._execute_with_retry(
                lambda: discogs_client.Client(self.user_agent, user_token=os.environ.get("DISCOGS_USER_TOKEN")),
                operation_name="Discogs client initialization"
            )
            if self.d_client:
                self.me = self._execute_with_retry(
                    self.d_client.identity,
                    operation_name="Discogs identity verification"
                )
                print(f"Successfully authenticated as: {self.me.name} (ID: {self.me.id})")
            else:
                raise Exception("Discogs client could not be initialized. Please check your token.")
        except Exception as e:
            print(f"Authentication failed: {e}")
            print("Please ensure your DISCOGS_USER_TOKEN environment variable is valid and correctly set.")
            raise # Re-raise to indicate failure to the calling system

    # Pattern 8: Robust Error Handling and Retries
    def _execute_with_retry(self, api_call_func, operation_name="API call"):
        """
        Executes a Discogs API call with exponential backoff and retries.

        Args:
            api_call_func (callable): The function to execute (e.g., self.d_client.identity).
            operation_name (str): A descriptive name for the operation for logging.

        Returns:
            Any: The result of the API call.

        Raises:
            Exception: If the API call fails after all retries.
        """
        for i in range(self._RETRY_ATTEMPTS):
            try:
                result = api_call_func()
                # Basic rate limiting: Discogs recommends 1 req/sec average.
                # The client library often handles this, but an explicit sleep helps with burst.
                time.sleep(0.5) # A small buffer after each successful call
                return result
            except HTTPError as e:
                if e.status_code == 429: # Too Many Requests
                    sleep_time = self._BASE_RETRY_DELAY_SECONDS * (2 ** i) + (time.monotonic() % 1)
                    print(f"Rate limit hit during {operation_name}. Retrying in {sleep_time:.2f} seconds... (Attempt {i+1}/{self._RETRY_ATTEMPTS})")
                    time.sleep(sleep_time)
                elif e.status_code in [500, 502, 503, 504]: # Server errors
                    sleep_time = self._BASE_RETRY_DELAY_SECONDS * (2 ** i) + (time.monotonic() % 1)
                    print(f"Server error ({e.status_code}) during {operation_name}. Retrying in {sleep_time:.2f} seconds... (Attempt {i+1}/{self._RETRY_ATTEMPTS})")
                    time.sleep(sleep_time)
                else:
                    print(f"HTTP error ({e.status_code}) during {operation_name}: {e.message}")
                    raise
            except Exception as e:
                print(f"An unexpected error occurred during {operation_name}: {e}")
                raise
        raise Exception(f"Failed to complete {operation_name} after {self._RETRY_ATTEMPTS} attempts.")

    # Pattern 9: Input Validation (Basic)
    def _validate_input(self, name, value, expected_type, min_val=None, max_val=None, allow_none=False):
        """
        Performs basic validation on function arguments.

        Args:
            name (str): The name of the argument (for error messages).
            value (any): The value of the argument.
            expected_type (type): The expected type (e.g., str, int).
            min_val (any, optional): Minimum allowed value for numbers.
            max_val (any, optional): Maximum allowed value for numbers.
            allow_none (bool, optional): Whether None is an allowed value.

        Returns:
            str: An error message if validation fails, otherwise None.
        """
        if value is None and not allow_none:
            return f"Error: '{name}' cannot be None."
        if value is not None and not isinstance(value, expected_type):
            return f"Error: '{name}' must be of type {expected_type.__name__}, but received {type(value).__name__}."
        if expected_type == str and value is not None and not value.strip():
            return f"Error: '{name}' cannot be an empty string."
        if expected_type == int and value is not None:
            if min_val is not None and value < min_val:
                return f"Error: '{name}' must be at least {min_val}."
            if max_val is not None and value > max_val:
                return f"Error: '{name}' cannot exceed {max_val}."
        return None

    # Pattern 3: Granular, Single-Purpose Functions
    # Pattern 5: Comprehensive Docstrings for AI Tools
    # Pattern 6: Descriptive Natural Language Returns for AI Tools

    @functools.lru_cache(maxsize=_CACHE_MAXSIZE)
    def _get_artist_object(self, artist_id: int) -> discogs_client.models.Artist:
        """
        Internal helper to fetch an artist object by ID, with caching.
        """
        print(f"DEBUG: CACHE MISS for _get_artist_object({artist_id}). Fetching from Discogs API.")
        artist = self._execute_with_retry(
            lambda: self.d_client.artist(artist_id),
            operation_name=f"fetching artist ID {artist_id}"
        )
        return artist

    @functools.lru_cache(maxsize=_CACHE_MAXSIZE)
    def _get_master_object(self, master_id: int) -> discogs_client.models.Master:
        """
        Internal helper to fetch a master object by ID, with caching.
        """
        print(f"DEBUG: CACHE MISS for _get_master_object({master_id}). Fetching from Discogs API.")
        master = self._execute_with_retry(
            lambda: self.d_client.master(master_id),
            operation_name=f"fetching master ID {master_id}"
        )
        return master

    # REFACTOR: get_collection_summary to mirror get_wantlist_summary's robustness
    @functools.lru_cache(maxsize=_DATA_CACHE_MAXSIZE) # Cache the list of ALL collection items
    def _get_all_collection_items(self) -> list:
        """
        [Internal Helper] Retrieves ALL collection items from the main folder.
        This is the expensive, rate-limited operation that should only run ONCE,
        with the result being cached.
        """
        print("DEBUG: CACHE MISS for _get_all_collection_items(). Fetching ALL collection items from Discogs API.")
        collection_folder_0 = self._execute_with_retry(
            lambda: self.me.collection_folders[0],
            operation_name="fetching main collection folder for all items"
        )
        # Convert PaginatedList to a full list to ensure consistent slicing and length
        return self._execute_with_retry(
            lambda: list(collection_folder_0.releases),
            operation_name="fetching all releases from collection folder"
        )

    def get_collection_summary(self, page: int = 1, per_page: int = 10) -> str:
            """
            Retrieves a summary of the authenticated user's Discogs music collection with pagination.
            This includes release titles, artists, and genres from the main collection folder.

            Purpose:
                To provide the AI with a quick overview of the user's collected music with pagination.

            Args:
                page (int): The page number to retrieve (1-indexed).
                per_page (int): The number of items to retrieve per page.

            Returns:
                str: A natural language string describing the collection, or an error message.
                    Example Success: "You have 3 items in your collection (Page 1 of 1):\n- 'Album Title 1' by Artist A (Genres: Pop, Rock)\n..."
                    Example No Items: "Your Discogs collection is empty."
                    Example Failure: "Failed to retrieve collection summary: Authentication required."
            """
            validation_error = (
                self._validate_input("page", page, int, min_val=1) or
                self._validate_input("per_page", per_page, int, min_val=1, max_val=100) # Added max_val for per_page
            )
            if validation_error:
                return validation_error

            try:
                # Use the new cached helper to get all collection items
                all_collection_items = self._get_all_collection_items()

                total_items = len(all_collection_items)
                if total_items == 0:
                    return "Your Discogs collection is empty."

                total_pages = (total_items + per_page - 1) // per_page

                if page > total_pages:
                    return f"Page {page} is out of range. Your collection has only {total_pages} page(s) (Total: {total_items} items)."

                start_index = (page - 1) * per_page
                end_index = start_index + per_page
                paginated_releases = all_collection_items[start_index:end_index]

                if not paginated_releases: # Should not happen if page <= total_pages for non-empty collection
                    return f"No items found on page {page} of your Discogs collection."

                summary_items = []
                for item in paginated_releases:
                    release = item.release # Each item in all_collection_items is a CollectionRelease object
                    artists = ", ".join([a.name for a in release.artists]) if release.artists else "N/A"
                    genres = ", ".join(release.genres) if release.genres else "N/A"
                    styles = ", ".join(release.styles) if release.styles else "N/A"

                    summary_items.append(f"- '{release.title}' by {artists} (Genres: {genres}), Styles: {styles})")

                return f"You have {total_items} items in your collection (Page {page} of {total_pages}):\n" + "\n".join(summary_items)
            except Exception as e:
                return f"Failed to retrieve collection summary: {e}"


    @functools.lru_cache(maxsize=_CACHE_MAXSIZE)
    def get_wantlist_summary(self, page: int = 1, per_page: int = 25) -> str:
        """
        Retrieves a summary of the authenticated user's Discogs wantlist with pagination.
        This includes release titles, artists, and genres from the wantlist.

        Purpose:
            To provide the AI with a quick overview of the music the user wants to acquire with pagination.

        Args:
            page (int): The page number to retrieve (1-indexed).
            per_page (int): The number of items to retrieve per page.

        Returns:
            str: A natural language string describing the wantlist, or an error message.
                 Example Success: "You have 2 items in your wantlist (Page 1 of 1):\n- 'Desired Album 1' by Artist X (Genres: Jazz)\n..."
                 Example No Items: "Your Discogs wantlist is empty."
                 Example Failure: "Failed to retrieve wantlist summary: Rate limit exceeded."
        """
        validation_error = (
            self._validate_input("page", page, int, min_val=1) or
            self._validate_input("per_page", per_page, int, min_val=1, max_val=100) # Added max_val for per_page
        )
        if validation_error:
            return validation_error

        try:
            # This fetches ALL wantlist items into a list.
            wantlist_items = self._execute_with_retry(
                lambda: list(self.me.wantlist), # Convert iterator to list to handle potential HTTPError during iteration
                operation_name="fetching wantlist"
            )
            if not wantlist_items:
                return "Your Discogs wantlist is empty."

            total_items = len(wantlist_items)
            total_pages = (total_items + per_page - 1) // per_page

            if page > total_pages:
                 return f"Page {page} is out of range. Your wantlist has only {total_pages} page(s) (Total: {total_items} items)."

            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_wantlist = wantlist_items[start_index:end_index]

            if not paginated_wantlist: # Should not happen if page <= total_pages for non-empty wantlist
                return f"No items found on page {page} of your Discogs wantlist."

            summary_items = []
            for item in paginated_wantlist:
                release = item.release
                artists = ", ".join([a.name for a in release.artists]) if release.artists else "N/A"
                genres = ", ".join(release.genres) if release.genres else "N/A"
                styles = ", ".join(release.styles) if release.styles else "N/A"
                summary_items.append(f"- '{release.title}' by {artists} (Genres: {genres}, Styles: {styles})")

            return f"You have {total_items} items in your wantlist (Page {page} of {total_pages}):\n" + "\n".join(summary_items)
        except Exception as e:
            return f"Failed to retrieve wantlist summary: {e}"

    # REFACTOR: get_collection_unique_artists to use the new internal _get_all_collection_items
    def get_collection_unique_artists(self) -> str:
        """
        Retrieves a list of unique artist names present in the user's Discogs collection.

        Purpose:
            To identify and list all distinct artists that the user has in their collection.
            The AI can then use these names for further searches or to understand the user's
            musical taste.

        Args:
            None

        Returns:
            str: A natural language string listing unique artist names, or an error message.
                 Example Success: "Artists in your collection: Artist A, Artist B, Artist C."
                 Example No Artists: "No unique artists found in your collection."
                 Example Failure: "Failed to retrieve unique artists from collection: Network error."
        """
        try:
            # Use the new cached helper to get all collection items
            all_collection_items = self._get_all_collection_items()

            unique_artists = set()
            if not all_collection_items:
                return "No unique artists found in your collection."

            for item in all_collection_items:
                release = item.release
                for artist in release.artists:
                    unique_artists.add(artist.name)

            if not unique_artists:
                return "No unique artists found in your collection."

            artists_list = sorted(list(unique_artists))
            # Limit to a reasonable number for AI processing and human readability
            display_count = min(len(artists_list), 20)
            displayed_artists = artists_list[:display_count]

            result = f"Found {len(artists_list)} unique artists in your collection: "
            result += ", ".join(displayed_artists)
            if len(artists_list) > display_count:
                result += " and more."
            return result
        except Exception as e:
            return f"Failed to retrieve unique artists from collection: {e}"

    # Pattern 4: No Lists as Arguments for AI-Facing Tools
    def search_artist_by_name(self, artist_name: str) -> str:
        """
        Searches for an artist by name on Discogs and returns their ID and main artist page URL.
        This tool prioritizes exact matches.

        Purpose:
            To find a Discogs artist ID based on a given name, which can then be used by other
            tools for more specific operations (e.g., retrieving discography).

        Args:
            artist_name (str): The full or partial name of the artist to search for.

        Returns:
            str: A natural language string containing the artist's name and ID if found,
                 or a message indicating no artist was found.
                 Example Success: "Found artist 'Boards of Canada' with ID: 18456. URL: https://www.discogs.com/artist/18456"
                 Example No Match: "Artist 'NonExistentBand' not found on Discogs."
                 Example Failure: "Failed to search for artist 'InvalidName': An unexpected error occurred."
        """
        validation_error = self._validate_input("artist_name", artist_name, str)
        if validation_error:
            return validation_error

        try:
            results = self._execute_with_retry(
                lambda: self.d_client.search(artist_name, type='artist'),
                operation_name=f"searching for artist '{artist_name}'"
            )

            artist_object = None
            # Prioritize exact match
            for res in results:
                if isinstance(res, discogs_client.models.Artist) and res.name.lower() == artist_name.lower():
                    artist_object = res
                    break

            # If no exact match, take the first artist result
            if not artist_object:
                for res in results:
                    if isinstance(res, discogs_client.models.Artist):
                        artist_object = res
                        break

            if artist_object:
                # The artist object will be implicitly cached if _get_artist_object is called later
                # with this ID, because _get_artist_object is now lru_cached.
                return (f"Found artist '{artist_object.name}' with ID: {artist_object.id}. \nDescription: {artist_object.profile}"
                        f"URL: {artist_object.url}")
            else:
                return f"Artist '{artist_name}' not found on Discogs."
        except Exception as e:
            return f"Failed to search for artist '{artist_name}': {e}"

    def search_master_release_by_name(self, release_title: str, artist_name: str = None, limit: int = 5) -> str:
        """
        Searches for master releases by title and optionally by artist on Discogs, returning the top results.

        Purpose:
            To find potential Discogs master release IDs based on a title, allowing an AI to see multiple
            options to choose from for more specific operations (e.g., retrieving a tracklist).

        Args:
            release_title (str): The title of the master release to search for.
            artist_name (str, optional): The name of the artist to narrow down the search.
            limit (int, optional): The maximum number of results to return (1-10). Defaults to 5.

        Returns:
            str: A natural language string listing the top master releases found, including their titles,
                artists, and IDs. Returns a message if no releases are found.
                Example Success: "Found 3 potential master releases for 'The Wall':\n1. 'The Wall' by Pink Floyd (ID: 406969)\n2. 'The Wall' by \"Weird Al\" Yankovic (ID: 2494669)\n3. 'The Wall Live 1980-81' by Pink Floyd (ID: 2379366)"
                Example No Match: "No master releases found matching 'NonExistentAlbum'."
        """
        # Input Validation
        validation_error = (
            self._validate_input("release_title", release_title, str) or
            self._validate_input("artist_name", artist_name, str, allow_none=True) or
            self._validate_input("limit", limit, int, min_val=1, max_val=10)
        )
        if validation_error:
            return validation_error

        # Build the search query
        query = release_title
        if artist_name and artist_name.strip():
            query += f" {artist_name}"

        try:
            # Execute the search
            results = self._execute_with_retry(
                lambda: self.d_client.search(query, type='master'),
                operation_name=f"searching for master release '{query}'"
            )

            # Iterate instead of slicing to avoid potential library bugs
            top_results = []
            for i, item in enumerate(results):
                if i >= limit:
                    break
                top_results.append(item)

            if not top_results:
                return f"No master releases found matching '{query}'."

            # Format the output string
            output_lines = [f"Found {len(top_results)} potential master releases for '{query}':"]
            for i, master in enumerate(top_results):
                # --- FIX: Get artists from the 'main_release' attribute on a search result ---
                artists = "Unknown Artist"
                if hasattr(master, 'main_release') and hasattr(master.main_release, 'artists'):
                    artists = ", ".join([artist.name for artist in master.main_release.artists])
                # --------------------------------------------------------------------------
                line = f"{i + 1}. '{master.title}' by {artists} (ID: {master.id})"
                output_lines.append(line)

            return "\n".join(output_lines)
        except Exception as e:
            return f"Failed to search for master release '{query}': {e}"

    # --- START REFACTORED SECTION ---

    @functools.lru_cache(maxsize=_DATA_CACHE_MAXSIZE) # Keep this for internal helper if you want to cache the full list
    def _get_all_artist_masters(self, artist_id: int) -> list:
        """
        [Internal Helper] Retrieves ALL master releases where the artist is primary.
        This is the expensive, rate-limited operation that should only run ONCE
        per artist, with the result being cached.

        Returns:
            A list of Master release objects or raises an exception.
        """
        print(f"DEBUG: CACHE MISS for _get_all_artist_masters(artist_id={artist_id}). Fetching ALL masters from API.")

        artist = self._get_artist_object(artist_id) # This call itself is cached

        filtered_masters = []
        # The /artists/{id}/releases endpoint mixes masters and regular releases.
        # We must iterate to filter, which is the main bottleneck.
        for release_item in artist.releases: # Renamed 'release' to 'release_item' to avoid confusion with Master objects
            # OPTIMIZATION 1: Filter by type first to avoid API calls on non-masters.
            if isinstance(release_item, discogs_client.models.Master):
                # To accurately check for primary artist, we must fetch the main_release.
                # This is an N+1 API call pattern, but it's now contained within this
                # single, one-time cached function.
                try:
                    main_release = self._execute_with_retry(
                        lambda: release_item.main_release, # Access main_release on the Master object
                        operation_name=f"fetching main_release for Master ID {release_item.id}"
                    )
                    # The main_release is a Release object, which DOES have an 'artists' attribute.
                    primary_artist_ids = [a.id for a in main_release.artists]
                    if artist_id in primary_artist_ids:
                        filtered_masters.append(release_item)
                except Exception as e:
                    print(f"DEBUG: Warning: Could not process Master ID {release_item.id} due to error: {e}")

        # Sort masters by year (most recent first) for a more useful default order.
        filtered_masters.sort(key=lambda m: m.year or 0, reverse=True)
        return filtered_masters

    def get_artist_master_releases_overview(self, artist_id: int, limit: int = 10, page: int = 1) -> str:
        """
        Retrieves a paginated list of master release titles for a given artist ID.
        Only includes Master releases where the specified artist is a primary artist.

        Purpose:
            To provide the AI with a concise list of major works (Master releases) by an artist,
            allowing it to browse discographies without being overwhelmed by every single release.

        Args:
            artist_id (int): The Discogs ID of the artist.
            limit (int, optional): The maximum number of master releases to return per page (1-50). Defaults to 10.
            page (int, optional): The page number to retrieve (starts from 1). Defaults to 1.

        Returns:
            str: A natural language string listing the master releases found, including pagination info,
                 or an error message.
                 Example Success: "Found 25 master releases for 'Artist Name'. Page 1/3 (10 shown):\n1. 'Master Title A' (2023) (Master ID: 12345)\n..."
                 Example No Masters: "No primary master releases found for Artist ID 999 ('Artist Name')."
                 Example Failure: "Failed to retrieve master releases for Artist ID 123: Artist not found."
        """
        print(f"\n--- Attempting to get master releases for artist_id={artist_id}, page={page} ---")

        validation_error = (
            self._validate_input("artist_id", artist_id, int, min_val=1) or
            self._validate_input("limit", limit, int, min_val=1, max_val=50) or
            self._validate_input("page", page, int, min_val=1)
        )
        if validation_error:
            return validation_error

        try:
            # Fetch artist object once for its name
            artist_obj = self._get_artist_object(artist_id) # This is cached and returns the Artist object
            artist_name = artist_obj.name # Correctly get the artist's name here

            # OPTIMIZATION: Call the new cached helper function.
            # If we've seen this artist_id before, this returns instantly from cache.
            all_masters = self._get_all_artist_masters(artist_id)

            total_masters = len(all_masters)
            if total_masters == 0:
                # Use the already fetched artist_name
                return f"No primary master releases found for Artist ID {artist_id} ('{artist_name}')."

            # OPTIMIZATION: Perform fast, in-memory pagination on the complete list.
            num_pages = (total_masters + limit - 1) // limit

            if page > num_pages:
                 return f"Page {page} is out of range. This artist has only {num_pages} page(s) of master releases (Total: {total_masters})."

            start_index = (page - 1) * limit
            end_index = start_index + limit
            paginated_masters = all_masters[start_index:end_index]

            # Use the already fetched artist_name directly
            output = (f"Found {total_masters} master releases for '{artist_name}'. "
                      f"Page {page}/{num_pages} ({len(paginated_masters)} shown):\n")
            for i, master in enumerate(paginated_masters):
                year = f" ({master.year})" if master.year else ""
                output += f"{start_index + i + 1}. '{master.title}'{year} (Master ID: {master.id})\n"

            return output.strip()

        except HTTPError as e:
            if e.status_code == 404:
                return f"Artist with ID {artist_id} not found on Discogs."
            return f"Failed to retrieve data for Artist ID {artist_id}: HTTP Error {e.status_code} - {e.message}"
        except Exception as e:
            # This will catch errors from the helper function if it fails the first time.
            return f"Failed to process master releases for Artist ID {artist_id}: An unexpected error occurred: {e}"
        

    @functools.lru_cache(maxsize=_CACHE_MAXSIZE)
    def get_master_release_tracklist(self, master_id: int, youtube_links=False) -> str:
        """
        Retrieves detailed information about the tracks of a specific Discogs Master release.

        Purpose:
            To allow the AI to explore the content of a Master release (e.g., an album)
            by listing its individual tracks, their durations, and position.

        Args:
            master_id (int): The Discogs ID of the Master release.
            youtube_links (bool): If set to true, it will return the youtube links for the tracks in the Discogs database.

        Returns:
            str: A natural language string describing the master release's tracklist,
                 or an error message.
                 Example Success: "Tracklist for 'Album Title' (Master ID: 12345):\n1. Track A (3:45)\n2. Track B (5:00)\n..."
                 Example No Tracks: "No tracklist found for Master ID 98765."
                 Example Failure: "Failed to retrieve tracklist for Master ID 1111: Master release not found."
        """
        # Pattern 9: Input Validation
        validation_error = self._validate_input("master_id", master_id, int, min_val=1)
        if validation_error:
            return validation_error

        try:
            master = self._get_master_object(master_id)

            information=""
            styles = ", ".join(master.styles) if hasattr(master, 'styles') and master.styles else 'N/A'
            genres = ", ".join(master.genres) if hasattr(master, 'genres') and master.genres else 'N/A'
            information = f"Genres: {genres}, Styles: {styles}"

            if not hasattr(master, 'tracklist') or not master.tracklist:
                return f"No tracklist found for Master ID {master_id} ('{master.title if hasattr(master, 'title') else 'Unknown Title'}')."

            output = f"Tracklist for '{master.title}' (Master ID: {master.id}). {information}:\n"
            for track in master.tracklist:
                position = track.position if hasattr(track, 'position') else 'N/A'
                title = track.title if hasattr(track, 'title') else 'Unknown Track'
                duration = track.duration if hasattr(track, 'duration') and track.duration else ''
                output += f"{position}. {title} ({duration.strip()})\n"

            if youtube_links:
                if not hasattr(master, 'videos') or not master.videos:
                    videos_message="This release has no youtube videos in the Discogs database"
                    output+=f"\n{videos_message}"
                else:
                    output+="\nYoutube links from Discogs database:"
                    for video in master.videos:
                        # --- START DEBUGGING ADDITION ---
                        print(f"DEBUG: Inspecting video object for title: '{getattr(video, 'title', 'N/A')}'")
                        print(f"DEBUG: Raw video object attributes: {video.__dict__ if hasattr(video, '__dict__') else 'N/A (not dict-like)'}")
                        print(f"DEBUG: Does video have 'uri' attribute? {hasattr(video, 'uri')}")
                        if hasattr(video, 'uri'):
                            print(f"DEBUG: Value of video.uri: '{video.uri}' (type: {type(video.uri)})")
                        # --- END DEBUGGING ADDITION ---

                        title=video.title if hasattr(video,'title') and video.title else "No title"
                        description=video.description if hasattr(video,'description') and video.description else "No description"
                        uri = video.data.get('uri')  if hasattr(video, 'data') and video.data and 'uri' in video.data else "No link"
                        videos_message=f"\nTitle: {title}, Description: {description}, Link: {uri}"
                        output+=videos_message

            return output.strip()
        except HTTPError as e:
            if e.status_code == 404:
                return f"Master release with ID {master_id} not found on Discogs."
            return f"Failed to retrieve tracklist for Master ID {master_id}: HTTP Error {e.status_code} - {e.message}"
        except Exception as e:
            return f"Failed to retrieve tracklist for Master ID {master_id}: An unexpected error occurred: {e}"


    @functools.lru_cache(maxsize=_DATA_CACHE_MAXSIZE)
    def _get_all_wantlist_items(self) -> list:
        """
        [Internal Helper] Retrieves ALL wantlist items from the user's Discogs account.
        This is the expensive, rate-limited operation that should only run ONCE,
        with the result being cached.
        """
        print("DEBUG: CACHE MISS for _get_all_wantlist_items(). Fetching ALL wantlist items from Discogs API.")
        # Convert PaginatedList to a full list to ensure consistent slicing and length
        return self._execute_with_retry(
            lambda: list(self.me.wantlist),
            operation_name="fetching all wantlist items"
        )


    def get_wantlist_unique_artists(self, page: int = 1, per_page: int = 25) -> str:
        """
        Retrieves a paginated list of unique artist names present in the user's Discogs wantlist.

        Purpose:
            To identify and list all distinct artists whose music the user desires, with pagination.
            The AI can use this to understand the user's desired musical taste,
            suggest related artists, or perform further searches on these artists.

        Args:
            page (int): The page number to retrieve (1-indexed).
            per_page (int): The number of unique artists to retrieve per page.

        Returns:
            str: A natural language string listing unique artist names, including pagination info,
                 or an error message.
                 Example Success: "Found 15 unique artists in your wantlist (Page 1 of 2):\n- Artist X\n- Artist Y\n..."
                 Example No Artists: "No unique artists found in your wantlist."
                 Example Failure: "Failed to retrieve unique artists from wantlist: Network error."
        """
        # Pattern 9: Input Validation
        validation_error = (
            self._validate_input("page", page, int, min_val=1) or
            self._validate_input("per_page", per_page, int, min_val=1, max_val=100) # Consistent with other paginated functions
        )
        if validation_error:
            return validation_error

        try:
            # Use the cached helper to get all wantlist items
            all_wantlist_items = self._get_all_wantlist_items()

            unique_artists = set()
            for item in all_wantlist_items:
                release = item.release
                if hasattr(release, 'artists') and release.artists:
                    for artist in release.artists:
                        unique_artists.add(artist.name)

            artists_list = sorted(list(unique_artists))
            total_artists = len(artists_list)

            if total_artists == 0:
                return "No unique artists found in your wantlist."

            total_pages = (total_artists + per_page - 1) // per_page

            if page > total_pages:
                return f"Page {page} is out of range. Your wantlist has only {total_pages} page(s) of unique artists (Total: {total_artists})."

            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_artists = artists_list[start_index:end_index]

            if not paginated_artists: # Should not happen if page <= total_pages for non-empty list
                return f"No unique artists found on page {page} of your Discogs wantlist."

            result = (f"Found {total_artists} unique artists in your wantlist (Page {page} of {total_pages}):\n"
                      + "\n".join([f"- {artist}" for artist in paginated_artists]))
            return result
        except Exception as e:
            return f"Failed to retrieve unique artists from wantlist: {e}"
        

# --- Example Usage (Pattern 7: Separate Internal Logging/Prints, shows how AI would interact) ---
if __name__ == "__main__":
    # Ensure you have a .env file in the same directory with DISCOGS_USER_TOKEN=<YOUR_DISCOGS_TOKEN>
    # and DISCOGS_AGENT_NAME=<YOUR_APP_NAME>
    # and discogs_client installed (pip install python-discogs-client python-dotenv)

    try:
        tools = DiscogsTools()
        print("\n--- AI Tool Demonstrations ---")

        # Example 1: Get Collection Summary
        print("\nCalling: get_collection_summary(page=1, per_page=5)")
        collection_summary = tools.get_collection_summary(page=1, per_page=5)
        print(f"AI receives:\n{collection_summary}")

        # Example 2: Get Collection Summary (page 2)
        print("\nCalling: get_collection_summary(page=2, per_page=5)")
        collection_summary_page2 = tools.get_collection_summary(page=2, per_page=5)
        print(f"AI receives:\n{collection_summary_page2}")

        # Example 3: Get Wantlist Summary
        print("\nCalling: get_wantlist_summary(page=1, per_page=5)")
        wantlist_summary = tools.get_wantlist_summary(page=1, per_page=5)
        print(f"AI receives:\n{wantlist_summary}")

        # Example 4: Get Unique Artists from Collection
        print("\nCalling: get_collection_unique_artists()")
        unique_artists = tools.get_collection_unique_artists()
        print(f"AI receives:\n{unique_artists}")

        # Example 5: Search Artist by Name
        artist_name = "Boards of Canada"
        print(f"\nCalling: search_artist_by_name(artist_name='{artist_name}')")
        artist_search_result = tools.search_artist_by_name(artist_name)
        print(f"AI receives: {artist_search_result}")

        if "ID:" in artist_search_result:
            try:
                boc_id = int(artist_search_result.split("ID:")[1].split(".")[0].strip())
                print(f"AI has extracted Artist ID: {boc_id}")
            except (ValueError, IndexError):
                boc_id = None
                print("AI could not extract Artist ID.")
        else:
            boc_id = None
            print("AI could not extract Artist ID.")

        # Example 6: Get Artist Master Releases Overview (FIRST call, will be SLOW and cache data)
        if boc_id:
            print(f"\n[DEMO] Calling get_artist_master_releases_overview(artist_id={boc_id}, page=1) for the first time.")
            print("[DEMO] Expect a delay and 'CACHE MISS' debug messages as it fetches all masters.")
            boc_masters_page1 = tools.get_artist_master_releases_overview(artist_id=boc_id, limit=3, page=1)
            print(f"AI receives (Page 1):\n{boc_masters_page1}")

            # Example 7: Get page 2 (SECOND call, will be INSTANT, using the cache)
            print(f"\n[DEMO] Calling get_artist_master_releases_overview(artist_id={boc_id}, page=2) immediately after.")
            print("[DEMO] This should be instantaneous. Note the ABSENCE of 'CACHE MISS' messages.")
            boc_masters_page2 = tools.get_artist_master_releases_overview(artist_id=boc_id, limit=3, page=2)
            print(f"AI receives (Page 2):\n{boc_masters_page2}")

            # Test out of bounds page
            print(f"\n[DEMO] Calling get_artist_master_releases_overview for a non-existent page (e.g., 999).")
            boc_masters_page_oob = tools.get_artist_master_releases_overview(artist_id=boc_id, limit=3, page=999)
            print(f"AI receives:\n{boc_masters_page_oob}")

            # Extract a master ID to test the next function
            first_master_id = None
            for line in boc_masters_page1.split('\n'):
                if "Master ID:" in line:
                    try:
                        first_master_id = int(line.split("Master ID:")[1].strip().replace(')', ''))
                        break
                    except (ValueError, IndexError):
                        continue

            if first_master_id:
                print(f"\nAI has extracted First Master ID: {first_master_id}")
                print(f"\nCalling: get_master_release_tracklist(master_id={first_master_id})")
                tracklist = tools.get_master_release_tracklist(master_id=first_master_id)
                print(f"AI receives:\n{tracklist}")
            else:
                print("\nAI could not extract a Master ID from the overview to test tracklist.")
        else:
            print("\nSkipping artist-specific tests as artist ID could not be extracted.")


        # Example 8: Testing error handling for invalid input (Pattern 9)
        print("\nCalling: get_artist_master_releases_overview(artist_id='invalid', limit=10, page=1)")
        invalid_input_result = tools.get_artist_master_releases_overview(artist_id='invalid', limit=10, page=1)
        print(f"AI receives: {invalid_input_result}")

        print("\nCalling: get_master_release_tracklist(master_id=99999999999)") # Non-existent ID
        non_existent_master = tools.get_master_release_tracklist(master_id=99999999999)
        print(f"AI receives: {non_existent_master}")

        print("\nCalling: get_collection_summary(page=0)") # Invalid page
        invalid_page_collection = tools.get_collection_summary(page=0)
        print(f"AI receives: {invalid_page_collection}")


    except Exception as e:
        print(f"\nTool initialization failed. Please check your Discogs token and internet connection: {e}")

