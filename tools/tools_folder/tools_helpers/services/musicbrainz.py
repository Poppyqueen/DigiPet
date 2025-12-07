import musicbrainzngs
from musicbrainzngs import WebServiceError, UsageError
from dotenv import load_dotenv
import os
import time
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
        """
        load_dotenv()  # Load environment variables from .env file
        self.app_name = os.environ.get("MUSICBRAINZ_APP_NAME")
        self.app_version = "1.0"
        self.contact = os.environ.get("MUSICBRAINZ_CONTACT")

        if not self.app_name or not self.contact:
            raise ValueError("MUSICBRAINZ_APP_NAME and MUSICBRAINZ_CONTACT must be set in the environment variables.")
        
        try:
            musicbrainzngs.set_useragent(self.app_name, self.app_version, self.contact)
        except Exception as e:
            print(f"Failed to initialize MusicBrainz user agent: {e}")

    def search_artists_by_name(self, artist_name: str, limit: int = 10, offset: int = 0) -> str:
        """
        Searches for artists by name with pagination support.

        Args:
            artist_name (str): The search query for the artist's name.
            limit (int, optional): The number of results to return per page. Max 100. Defaults to 10.
            offset (int, optional): The starting point of the result set, used for pagination. 
                                    To get the next page, set offset to `offset + limit`. Defaults to 0.

        Returns:
            str: A paginated, natural language summary of search results.
        """
        try:
            result = musicbrainzngs.search_artists(artist=artist_name, limit=limit, offset=offset)
            time.sleep(1)
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
        
    def get_artist_details_and_works(self, artist_id: str, target_types: list = None, limit: int = 25, offset: int = 0) -> str:
        """
        Retrieves artist info and a list of their works (Release Groups).
        
        Args:
            artist_id (str): The unique MusicBrainz ID of the artist.
            target_types (list, optional): Filter by type. Examples: ['album'], ['single'], ['ep'], ['compilation']. 
                                           If None, returns ALL types.
            limit (int, optional): Results per page. Defaults to 25.
            offset (int, optional): Pagination offset. Defaults to 0.
        """
        try:
            # Get artist details
            artist_info_response = musicbrainzngs.get_artist_by_id(artist_id, includes=['annotation'])
            time.sleep(1)
            artist = artist_info_response.get('artist', {})

            if not artist:
                return f"Could not find details for artist ID '{artist_id}'."

            name = artist.get('name', 'N/A')
            annotation_text = artist.get('annotation', {}).get('text', 'N/A')
            summary = f"Details for {name} (ID: {artist_id}):\n"
            summary += f"- Country: {artist.get('country', 'N/A')}\n"
            summary += f"- Type: {artist.get('type', 'N/A')}\n"
            summary += f"- Annotation: {annotation_text}\n"
            
            # Prepare arguments for browse_release_groups
            # FIX: Only include 'release_type' in kwargs if target_types has a value.
            # Passing 'release_type=None' can cause 'NoneType not iterable' errors in the library.
            browse_kwargs = {
                'artist': artist_id,
                'limit': limit,
                'offset': offset
            }
            if target_types:
                browse_kwargs['release_type'] = target_types
            time.sleep(1)
            rg_results = musicbrainzngs.browse_release_groups(**browse_kwargs)
            
            release_groups = rg_results.get('release-group-list', [])
            total_rg_count = rg_results.get('release-group-count', 0)

            type_desc = "Works" if not target_types else ", ".join(target_types)

            if not release_groups:
                summary += f"\nThis artist has no {type_desc} listed on the current page."
            else:
                summary += f"\n{type_desc} (showing {offset + 1}-{offset + len(release_groups)} of {total_rg_count} total):\n"
                for i, rg in enumerate(release_groups):
                    title = rg.get('title', 'N/A')
                    rg_type = rg.get('primary-type', 'Unspecified')
                    secondary_types = rg.get('secondary-type-list', [])
                    if secondary_types:
                        rg_type += f" + {', '.join(secondary_types)}"
                        
                    rg_id = rg.get('id', 'N/A')
                    summary += f"- {title} ({rg_type}) - Use Release Group ID: {rg_id}\n"

            if total_rg_count > offset + len(release_groups):
                summary += f"\nNote: More results available. Call again with `offset={offset + limit}`."

            return summary.strip()

        except WebServiceError as e:
            return f"An error occurred while fetching artist details: {e}"
        except TypeError as e:
            return f"Type error in arguments: {e}"
        
    def get_tracklist(self, release_group_id: str) -> str:
        """
        Retrieves the tracklist for a Release Group (Album, EP, Single) identified by its ID.
        """
        try:
            # Get the release group details
            rg_info = musicbrainzngs.get_release_group_by_id(
                release_group_id,
                includes=['releases', 'artist-credits']
            )
            time.sleep(1)

            release_group = rg_info.get('release-group', {})
            if not release_group:
                return f"Could not find release group with ID '{release_group_id}'."

            work_title = release_group.get('title', 'N/A')
            
            # Artist extraction
            artist_credit = release_group.get('artist-credit', [])
            work_artist = 'N/A'
            if artist_credit:
                names = [ac.get('name', '') for ac in artist_credit if isinstance(ac, dict)]
                joined_names = ", ".join(name for name in names if name)
                if joined_names:
                    work_artist = joined_names

            releases = release_group.get('release-list', [])
            if not releases:
                return f"No releases found for '{work_title}'. Cannot retrieve tracklist."

            # Find a suitable release (Official > CD/Digital > Any)
            target_release_id = None
            for release in releases:
                status = release.get('status')
                medium_list = release.get('medium-list', [])
                medium_format = medium_list[0].get('format') if medium_list else None
                
                if status == 'official' and (medium_format == 'CD' or medium_format == 'Digital Media'):
                    target_release_id = release.get('id')
                    break
                elif not target_release_id and status == 'official': 
                    target_release_id = release.get('id')
                elif not target_release_id: 
                    target_release_id = release.get('id')
            
            if not target_release_id:
                return f"Could not determine a suitable release to get tracks for '{work_title}'."

            # Get details of the selected release
            release_details = musicbrainzngs.get_release_by_id(
                target_release_id,
                includes=['recordings', 'media', 'artists', 'annotation']
            )
            time.sleep(1)

            current_release = release_details.get('release', {})
            annotation_text = current_release.get('annotation', {}).get('text', 'N/A')
            summary = f"Tracklist for '{work_title}' by {work_artist} (Release Group ID: {release_group_id}):\n"
            summary += f"(Based on release: '{current_release.get('title', 'N/A')}' - Release ID: {target_release_id})\n\n"
            summary += f"Annotation: {annotation_text}\n"

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
                        # Get track title from the 'recording' object
                        track_title = track.get('recording', {}).get('title', 'N/A')
                        track_length_ms = track.get('length')
                        
                        # Format duration
                        duration_str = "N/A"
                        if track_length_ms:
                            total_seconds = int(track_length_ms) // 1000
                            minutes = total_seconds // 60
                            seconds = total_seconds % 60
                            duration_str = f"{minutes:02d}:{seconds:02d}"

                        # Determine track artist
                        # FIX: Renamed 'album_artist' to 'work_artist' to match earlier definition
                        track_artist = work_artist 
                        track_artist_credit = track.get('artist-credit')
                        if not track_artist_credit:
                            track_artist_credit = track.get('recording', {}).get('artist-credit')

                        if track_artist_credit:
                            track_artist_names = [ac.get('name', '') for ac in track_artist_credit if isinstance(ac, dict)]
                            joined_track_artist_names = ", ".join(name for name in track_artist_names if name)
                            if joined_track_artist_names:
                                track_artist = joined_track_artist_names

                        track_num = track.get('position', i + 1)
                        summary += f"{track_num}. {track_title}"
                        
                        # Only show track artist if it's different from album artist
                        if track_artist and track_artist != work_artist and track_artist != 'N/A':
                            summary += f" (by {track_artist})"
                        summary += f" [{duration_str}]\n"
                summary += "\n"

            return summary.strip()

        except WebServiceError as e:
            return f"An error occurred while fetching album tracklist: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"
        
    def search_release_group(self, query: str, artist_name: str = None, limit: int = 5) -> str:
        """
        Searches for Release Groups (Albums, Singles, EPs, etc.) by name.
        """
        try:
            search_fields = {"releasegroup": query}
            if artist_name:
                search_fields["artist"] = artist_name

            results = musicbrainzngs.search_release_groups(
                limit=min(limit, 100), 
                **search_fields
            )
            time.sleep(1)

            all_release_groups = results.get('release-group-list', [])
            
            if not all_release_groups:
                return f"No releases found matching '{query}'."

            summary = f"Found {results.get('release-group-count', 0)} matches for '{query}'"
            if artist_name:
                summary += f" by '{artist_name}'"
            summary += ":\n"

            for i, rg in enumerate(all_release_groups):
                title = rg.get('title', 'N/A')
                rg_type = rg.get('primary-type', 'N/A')
                rg_id = rg.get('id', 'N/A')
                
                # Get artist credits
                artist_credit = rg.get('artist-credit', [])
                album_artist = 'N/A' 
                if artist_credit:
                    names = [ac.get('name', '') for ac in artist_credit if isinstance(ac, dict)]
                    joined_names = ", ".join(name for name in names if name) 
                    if joined_names:
                        album_artist = joined_names

                summary += f"{i+1}. {title}"
                if album_artist != 'N/A':
                    summary += f" by {album_artist}"
                summary += f" ({rg_type}) - Use Release Group ID: {rg_id}\n"
            
            return summary.strip()

        except WebServiceError as e:
            return f"An error occurred while searching: {e}"
        
    def search_by_raw_lucene(self, entity_type: str, raw_lucene: str, limit: int = 10, offset: int = 0) -> str:
        """
        Performs a search against the MusicBrainz database for a specified entity type
        using a raw Lucene query string.
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

            result = search_function(query=raw_lucene, limit=limit, offset=offset)
            entity_list = result.get(result_key, [])
            time.sleep(1)
            total_count = result.get(f'{entity_type}-count', 0)

            if not entity_list:
                return f"No {entity_type}s found matching the raw Lucene query '{raw_lucene}' at the current page."

            page_info = f"Showing results {offset + 1}-{offset + len(entity_list)} of {total_count} total {entity_type}s"
            summary = f"{page_info} matching your query:\n"
            
            for i, entity in enumerate(entity_list):
                name = entity.get('title', entity.get('name', 'N/A'))
                entity_id = entity.get('id', 'N/A')
                
                details = []
                
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
                
                tag_list = entity.get('tag-list', [])
                if tag_list:
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