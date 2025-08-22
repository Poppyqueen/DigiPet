import musicbrainzngs
from musicbrainzngs import WebServiceError, UsageError
from dotenv import load_dotenv
import os
# Set a default hostname for all operations.


musicbrainzngs.set_hostname("musicbrainz.org")

class MusicBrainzSearchTools:
    """
    A streamlined toolset for searching and retrieving information from the
    MusicBrainz database, with a special focus on searching by genre and other
    folksonomy tags. This toolset is read-only and supports pagination.
    """

    def __init__(self):
        """
        Initializes the MusicBrainzSearchTools class and sets the user agent
        required for all API requests.

        Args:
            app_name (str): The name of the application using the tool.
            app_version (str): The version of the application.
            contact (str): A URL or email address for the application's developer.
        """
        load_dotenv()  # Load environment variables from .env file
        self.app_name = os.environ.get("MUSICBRAINZ_APP_NAME")
        self.app_version = "1.0"
        self.contact = os.environ.get("MUSICBRAINZ_CONTACT")
        
        try:
            musicbrainzngs.set_useragent(self.app_name, self.app_version, self.contact)
        except Exception as e:
            # This helps in debugging initialization issues.
            print(f"Failed to initialize MusicBrainz user agent: {e}")

    def search_artists_by_name(self, artist_name: str, limit: int = 10, offset: int = 0) -> str:
        """
        Searches for artists by name with pagination support.

        Args:
            artist_name (str): The search query for the artist's name.
            limit (int, optional): The number of results to return per page. Max 100. Defaults to 10.
            offset (int, optional): The starting point of the result set, used for pagination. To get the next page, set offset to `offset + limit`. Defaults to 0.

        Returns:
            str: A paginated, natural language summary of search results, including total count, artist names, and their MusicBrainz IDs.
        """
        try:
            result = musicbrainzngs.search_artists(artist=artist_name, limit=limit, offset=offset)
            artist_list = result.get('artist-list', [])
            total_count = result.get('artist-count', 0)
            
            if not artist_list:
                return f"No artists found matching the name '{artist_name}' at the current page."
                
            page_info = f"Showing results {offset + 1}-{offset + len(artist_list)} of {total_count} total artists"
            summary = f"{page_info} matching '{artist_name}':\n"

            for i, artist in enumerate(artist_list):
                name = artist.get('name', 'N/A')
                artist_id = artist.get('id', 'N/A')
                disambiguation = artist.get('disambiguation', '')
                summary += f"{offset + i + 1}. {name}"
                if disambiguation:
                    summary += f" ({disambiguation})"
                summary += f" - Use ID: {artist_id}\n"

            if total_count > offset + len(artist_list):
                summary += f"\nNote: More results are available. To get the next page, call this tool again with `offset={offset + limit}`."

            return summary.strip()

        except WebServiceError as e:
            return f"An error occurred while searching for artists: {e}"
        
    def get_artist_details_and_albums(self, artist_id: str, limit: int = 25, offset: int = 0) -> str:
        """
        Retrieves detailed information for a specific artist and a paginated list of their primary albums and EPs using their MusicBrainz ID.

        Args:
            artist_id (str): The unique MusicBrainz ID of the artist, found via a search tool.
            limit (int, optional): The number of albums/EPs to return per page. Max 100. Defaults to 25.
            offset (int, optional): The starting point of the album/EP list, used for pagination. To get the next page, set offset to `offset + limit`. Defaults to 0.

        Returns:
            str: A natural language string detailing the artist's information and a paginated list of their albums with their Release Group IDs.
        """
        try:
            # Get artist details
            artist_info_response = musicbrainzngs.get_artist_by_id(artist_id)
            artist = artist_info_response.get('artist', {})

            if not artist:
                return f"Could not find details for artist ID '{artist_id}'."

            name = artist.get('name', 'N/A')
            summary = f"Details for {name} (ID: {artist_id}):\n"
            summary += f"- Country: {artist.get('country', 'N/A')}\n"
            summary += f"- Type: {artist.get('type', 'N/A')}\n"
            if artist.get('life-span', {}).get('begin'):
                summary += f"- Life Span: {artist['life-span']['begin']}"
                if artist['life-span'].get('end'):
                    summary += f" to {artist['life-span']['end']}"
                summary += "\n"
            
            # Now, browse for release groups associated with this artist, with pagination
            rg_results = musicbrainzngs.browse_release_groups(
                artist=artist_id, 
                # FIX: Narrow the release_type filter to explicitly "album" and "ep"
                # as requested by the prompt ("primary albums and EPs").
                # The previous broad list might be causing unexpected filtering behavior.
                release_type=["album", "ep"], 
                limit=limit, 
                offset=offset
            )

            print(rg_results)
            
            release_groups = rg_results.get('release-group-list', [])
            total_rg_count = rg_results.get('release-group-count', 0)

            if not release_groups:
                summary += "\nThis artist has no albums or EPs listed on the current page."
            else:
                summary += f"\nAlbums and EPs (showing {offset + 1}-{offset + len(release_groups)} of {total_rg_count} total):\n"
                for i, rg in enumerate(release_groups):
                    title = rg.get('title', 'N/A')
                    rg_type = rg.get('primary-type', 'N/A')
                    rg_id = rg.get('id', 'N/A')
                    summary += f"- {title} ({rg_type}) - Use Release Group ID: {rg_id}\n"

            if total_rg_count > offset + len(release_groups):
                summary += f"\nNote: More albums/EPs are available. To get the next page, call this tool again with `offset={offset + limit}`."

            return summary.strip()

        except WebServiceError as e:
            return f"An error occurred while fetching artist details or albums: {e}"
        
    def get_album_tracklist(self, release_group_id: str) -> str:
        """
        Retrieves the tracklist for an album (Release Group) identified by its MusicBrainz ID.
        It attempts to find an 'official' CD or Digital Media release to get the tracklist from.

        Args:
            release_group_id (str): The unique MusicBrainz Release Group ID of the album.

        Returns:
            str: A natural language string detailing the album's tracklist across its discs/media.
        """
        try:
            # First, get the release group details including its releases
            rg_info = musicbrainzngs.get_release_group_by_id(
                release_group_id,
                includes=['releases', 'artist-credits'] # We need releases to find tracks, and artist-credits for the album name
            )

            release_group = rg_info.get('release-group', {})
            if not release_group:
                return f"Could not find release group with ID '{release_group_id}'."

            album_title = release_group.get('title', 'N/A')
            
            # --- FIX for album_artist being empty ---
            artist_credit = release_group.get('artist-credit', [])
            album_artist = 'N/A' # Default to N/A
            if artist_credit:
                # Extract names, ensuring they are not empty strings, and only process dicts
                names = [ac.get('name', '') for ac in artist_credit if isinstance(ac, dict)]
                joined_names = ", ".join(name for name in names if name) # Join only non-empty names
                if joined_names: # If after filtering, there are still names
                    album_artist = joined_names
            # --- End FIX ---

            releases = release_group.get('release-list', [])
            if not releases:
                return f"No releases found for the album '{album_title}' (ID: {release_group_id}). Cannot retrieve tracklist."

            # Find a suitable release to get the tracklist from.
            # Prioritize 'official' releases, then 'CD' or 'Digital Media' formats.
            # If multiple, just take the first one that fits the criteria.
            target_release_id = None
            for release in releases:
                status = release.get('status')
                # Ensure 'medium-list' exists and has at least one item before accessing format
                medium_format = release.get('medium-list', [{}])[0].get('format') if release.get('medium-list') else None
                
                # Prioritize official CD/Digital releases
                if status == 'official' and (medium_format == 'CD' or medium_format == 'Digital Media'):
                    target_release_id = release.get('id')
                    break
                elif not target_release_id and status == 'official': # Fallback to any official release
                    target_release_id = release.get('id')
                elif not target_release_id and (medium_format == 'CD' or medium_format == 'Digital Media'): # Fallback to any CD/Digital
                    target_release_id = release.get('id')
                elif not target_release_id: # Last resort: just take the very first release
                    target_release_id = release.get('id')
            
            if not target_release_id:
                return f"Could not determine a suitable release to get tracks for album '{album_title}' (ID: {release_group_id})."

            # Now, get the details of the selected release, including its tracks
            release_details = musicbrainzngs.get_release_by_id(
                target_release_id,
                includes=['recordings', 'media', 'artists'] # 'recordings' gives track info, 'media' for disc info, 'artists' for track artist credits
            )

            current_release = release_details.get('release', {})
            if not current_release:
                return f"Could not retrieve details for selected release ID '{target_release_id}'."

            summary = f"Tracklist for '{album_title}' by {album_artist} (Release Group ID: {release_group_id}):\n"
            summary += f"(Based on release: '{current_release.get('title', 'N/A')}' - Release ID: {target_release_id})\n\n"

            media_list = current_release.get('medium-list', [])
            if not media_list:
                summary += "No media or tracks found for this specific release."
                return summary

            for medium in media_list:
                medium_position = medium.get('position', 1)
                medium_format = medium.get('format', 'N/A')
                track_list = medium.get('track-list', [])

                summary += f"--- Disc {medium_position} ({medium_format}) ---\n"
                if not track_list:
                    summary += "No tracks found on this disc.\n"
                else:
                    for i, track in enumerate(track_list):
                        # --- FIX for track_title being N/A ---
                        # Get track title from the 'recording' object, as it's the canonical source.
                        # The 'title' key directly on the 'track' object can sometimes be missing or less reliable.
                        track_title = track.get('recording', {}).get('title', 'N/A')
                        # --- End FIX ---
                        
                        track_length_ms = track.get('length') # This is the length of the track as it appears on the release
                        
                        # Format duration
                        duration_str = "N/A"
                        if track_length_ms:
                            # Convert milliseconds to seconds
                            total_seconds = int(track_length_ms) // 1000
                            minutes = total_seconds // 60
                            seconds = total_seconds % 60
                            duration_str = f"{minutes:02d}:{seconds:02d}"

                        # Get track-specific artist credit if available, otherwise use album's artist
                        # --- Apply robust artist name extraction for track artists too ---
                        track_artist = album_artist # Default to album artist
                        track_artist_credit = track.get('artist-credit')
                        if not track_artist_credit: # If no artist credit directly on the track, check the recording
                            track_artist_credit = track.get('recording', {}).get('artist-credit')

                        if track_artist_credit:
                            track_artist_names = [ac.get('name', '') for ac in track_artist_credit if isinstance(ac, dict)]
                            joined_track_artist_names = ", ".join(name for name in track_artist_names if name)
                            if joined_track_artist_names:
                                track_artist = joined_track_artist_names
                        # --- End robust artist name extraction ---

                        track_num = track.get('position', i + 1)
                        summary += f"{track_num}. {track_title}"
                        # Only show track artist if it's different from album artist AND not N/A (or empty)
                        if track_artist and track_artist != album_artist and track_artist != 'N/A':
                            summary += f" (by {track_artist})"
                        summary += f" [{duration_str}]\n"
                summary += "\n" # Add a newline between discs

            return summary.strip()

        except WebServiceError as e:
            return f"An error occurred while fetching album tracklist: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"
        
    def search_album_by_name(self, album_name: str, artist_name: str = None, limit: int = 5) -> str:
        """
        Searches for albums (Release Groups) by name, optionally filtered by artist,
        and returns a list of matching Release Group IDs.

        Args:
            album_name (str): The name of the album to search for.
            artist_name (str, optional): The name of the artist to refine the search.
            limit (int, optional): The maximum number of results to return. Max 100. Defaults to 5.

        Returns:
            str: A natural language string listing the found albums with their Release Group IDs,
                 or a message if no albums are found.
        """
        try:
            search_fields = {"releasegroup": album_name}
            if artist_name:
                search_fields["artist"] = artist_name

            # FIX: 'release_type' is NOT a valid parameter for musicbrainzngs.search_release_groups.
            # We will perform the search and then filter the results by primary-type in Python.
            results = musicbrainzngs.search_release_groups(
                limit=min(limit, 100), # Ensure limit doesn't exceed 100 for the API call
                **search_fields
            )

            all_release_groups = results.get('release-group-list', [])
            
            # Filter the results in Python to only include 'Album' or 'EP' primary types.
            # MusicBrainz API typically returns 'primary-type' with initial capitalization.
            filtered_release_groups = [
                rg for rg in all_release_groups
                if rg.get('primary-type') in ['Album', 'EP']
            ]

            # Get the total count of results from the API before filtering (for informational purposes)
            total_results_unfiltered = results.get('release-group-count', 0) 
            
            # The count we will actually display and work with
            total_filtered_results = len(filtered_release_groups)

            if not filtered_release_groups:
                if artist_name:
                    return f"No primary albums or EPs found matching '{album_name}' by '{artist_name}'."
                else:
                    return f"No primary albums or EPs found matching '{album_name}'."

            summary = f"Found {total_filtered_results} primary albums or EPs matching '{album_name}'"
            if artist_name:
                summary += f" by '{artist_name}'"
            summary += ":\n"

            for i, rg in enumerate(filtered_release_groups): # Iterate over the filtered list
                title = rg.get('title', 'N/A')
                rg_type = rg.get('primary-type', 'N/A')
                rg_id = rg.get('id', 'N/A')
                
                # Get artist credits for clarity, using robust extraction
                artist_credit = rg.get('artist-credit', [])
                album_artist = 'N/A' 
                if artist_credit:
                    names = [ac.get('name', '') for ac in artist_credit if isinstance(ac, dict)]
                    joined_names = ", ".join(name for name in names if name) 
                    if joined_names:
                        album_artist = joined_names

                summary += f"{i+1}. Title: '{title}'"
                if album_artist != 'N/A':
                    summary += f" by {album_artist}"
                summary += f" ({rg_type}) - Use Release Group ID: {rg_id}\n"
            
            # Provide a note if there might be more results than displayed (due to limit or post-filtering)
            if total_filtered_results < total_results_unfiltered and total_filtered_results < limit:
                # If we filtered down the results and also hit the limit, or just filtered down
                summary += f"\nNote: There may be more matching albums/EPs. Consider refining your search terms."
            elif total_filtered_results == limit:
                # If we reached the limit for the *filtered* results
                summary += f"\nNote: Reached display limit of {limit} results. There may be more matching albums/EPs."


            return summary.strip()

        except WebServiceError as e:
            return f"An error occurred while searching for albums: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"
        
    def search_by_raw_lucene(self, entity_type: str, raw_lucene: str, limit: int = 10, offset: int = 0) -> str:
        """
        Performs a search against the MusicBrainz database for a specified entity type
        using a raw Lucene query string. This function assumes the query is
        correctly formatted Lucene syntax and will not perform any validation or transformation.
        
        This tool is useful for advanced users who want to construct complex
        queries that are not possible with the other tools.

        Args:
            entity_type (str): The type of entity to search for. Must be 'artist', 'release-group', or 'recording'.
            raw_lucene (str): The Lucene query string to be used directly for the search.
                            Example: 'artist:"The Beatles" AND country:GB'
            limit (int, optional): The number of results to return per page. Max 100. Defaults to 10.
            offset (int, optional): The starting point of the result set, used for pagination.
                                    Defaults to 0.

        Returns:
            str: A paginated, natural language summary of search results, including total count and
                relevant details for the specified entity type. Results will also include associated
                tags (genres, styles) if available.
        """
        valid_entities = ['artist', 'release-group', 'recording']
        if entity_type not in valid_entities:
            return f"Invalid entity_type: '{entity_type}'. Please use one of: {', '.join(valid_entities)}."
        
        if not raw_lucene:
            return "No raw_lucene query provided. Please provide a valid Lucene query string."

        try:
            search_function = None
            result_key = None
            
            if entity_type == 'artist':
                search_function = musicbrainzngs.search_artists
                result_key = 'artist-list'
            elif entity_type == 'release-group':
                search_function = musicbrainzngs.search_release_groups
                result_key = 'release-group-list'
            elif entity_type == 'recording':
                search_function = musicbrainzngs.search_recordings
                result_key = 'recording-list'

            if not search_function:
                return "An internal error occurred: No search function mapped to the entity type."

            # The search endpoint includes tags by default if they exist
            result = search_function(query=raw_lucene, limit=limit, offset=offset)
            entity_list = result.get(result_key, [])
            total_count = result.get(f'{entity_type}-count', 0)

            if not entity_list:
                return f"No {entity_type}s found matching the raw Lucene query '{raw_lucene}' at the current page."

            page_info = f"Showing results {offset + 1}-{offset + len(entity_list)} of {total_count} total {entity_type}s"
            summary = f"{page_info} matching your query:\n"
            
            for i, entity in enumerate(entity_list):
                name = entity.get('title', entity.get('name', 'N/A'))
                entity_id = entity.get('id', 'N/A')
                
                # This list will hold all descriptive parts of the result string
                details = []
                
                # Add entity-specific details
                if entity_type == 'artist':
                    disambiguation = entity.get('disambiguation', '')
                    if disambiguation:
                        details.append(f"({disambiguation})")
                elif entity_type == 'release-group':
                    artist_name = entity.get('artist-credit-phrase', 'N/A')
                    details.append(f"by {artist_name}")
                elif entity_type == 'recording':
                    artist_name = entity.get('artist-credit-phrase', 'N/A')
                    details.append(f"by {artist_name}")
                    release_list = entity.get('release-list')
                    if release_list:
                        release_title = release_list[0].get('title', 'N/A')
                        details.append(f"on '{release_title}'")
                
                # NEW: Add tags (genres, styles, etc.) if they exist
                tag_list = entity.get('tag-list', [])
                if tag_list:
                    # Filter for tags that have been voted on and get their names
                    tag_names = [tag['name'] for tag in tag_list if tag.get('count', 0) > 0]
                    if tag_names:
                        details.append(f"[Tags: {', '.join(tag_names)}]")
                
                detail_string = " ".join(details)
                
                summary += f"{offset + i + 1}. {name}"
                if detail_string:
                    summary += f" {detail_string}"
                summary += f" - Use ID: {entity_id}\n"

            if total_count > offset + len(entity_list):
                summary += f"\nNote: More results are available. To get the next page, call this tool again with `offset={offset + limit}`."

            return summary.strip()

        except WebServiceError as e:
            return f"An error occurred while searching: {e}"
        except UsageError as e:
            return f"An error occurred with the query. The Lucene syntax might be incorrect. Error: {e}"