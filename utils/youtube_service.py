import os
import time
from typing import List, Optional, Dict

import webbrowser

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- Configuration Constants ---
YOUTUBE_API_SCOPES = ["https://www.googleapis.com/auth/youtube"]
TOKEN_FILE = "bots/secrets/youtube_token.json" # bots is a secret folder protected by gitignore, make sure yours is the same

class YouTubeTools:
    """
    A collection of self-contained tools for interacting with the YouTube Data API.

    This class handles its own authentication and provides discrete methods for:
    1. Searching YouTube videos (returning a single best match with title and ID).
    2. Creating new, private YouTube playlists.
    3. Adding individual videos to an existing YouTube playlist.

    Each method is designed to be interpretable and callable by an AI/LLM,
    adhering to a schema that prefers single entries per argument and
    returns informative natural language string outputs.
    """

    def __init__(self, client_secrets_file: str = "bots/secrets/client_secrets.json"):
        """
        Initializes the YouTubeTools service by authenticating with the YouTube Data API.

        This method attempts to load existing user credentials from `youtube_token.json`.
        If valid credentials are not found (e.g., first run, expired, or invalid),
        it initiates the OAuth 2.0 authorization flow. This flow typically opens
        a browser window for the user to grant permissions to the application.
        The obtained credentials are then saved to `youtube_token.json` for future use.

        Args:
            client_secrets_file (str): The path to your Google API client secrets JSON file.
                                       This file is obtained from the Google Cloud Console.
                                       Defaults to "client_secrets.json" in the current directory.

        Raises:
            FileNotFoundError: If the specified `client_secrets_file` does not exist.
            Exception: For general authentication failures or issues building the service.
        """
        if not os.path.exists(client_secrets_file):
            raise FileNotFoundError(
                f"Client secrets file not found at: {client_secrets_file}. "
                "Please ensure it's in the correct directory and named 'client_secrets.json'."
            )
        self.client_secrets_file = client_secrets_file
        self.service = self._authenticate_youtube_service()
        # Internal print for initialization status, not part of AI tool output
        print("YouTubeTools initialized successfully and authenticated.")

        self.latest_playlist_info={}
        self.latests_playlist_videos=[]

    def _authenticate_youtube_service(self):
        """
        Handles the authentication process for the YouTube Data API.

        It first tries to load credentials from `TOKEN_FILE`. If credentials are
        not found or are expired, it initiates a new OAuth 2.0 flow using `InstalledAppFlow`.
        The new credentials are then saved to `TOKEN_FILE`.

        Returns:
            googleapiclient.discovery.Resource: An authenticated YouTube Data API service object.
        """
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, YOUTUBE_API_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}. Re-authenticating...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_file, YOUTUBE_API_SCOPES
                    )
                    creds = flow.run_local_server(port=8080)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, YOUTUBE_API_SCOPES
                )
                creds = flow.run_local_server(port=8080)

            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

        return build('youtube', 'v3', credentials=creds)

    def _execute_with_retry(self, api_request_builder, max_retries: int = 5, base_delay: int = 1):
        """
        Helper method to execute an API call with exponential backoff and retry logic
        for transient errors (e.g., rate limits, server errors).
        Internal method, so it can print.
        """
        for i in range(max_retries):
            try:
                return api_request_builder().execute()
            except HttpError as e:
                if e.resp.status in [429, 500, 502, 503, 504] and i < max_retries - 1:
                    sleep_time = base_delay * (2 ** i) + (time.monotonic() % 1)
                    print(f"YouTube API error: {e.resp.status} - {e.content.decode()}. Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                else:
                    raise # Re-raise for non-retryable errors or max retries reached
            except Exception as e:
                raise # Re-raise for other types of errors
        return {}
    
    def search_video(self, query: str, max_results: int = 10, category_id: str = '10') -> List[Dict[str, str]]:
        """
        Searches YouTube for videos matching a given query and returns a structured list
        of the top N matching videos, including their titles and IDs.

        This tool is useful for finding specific songs, music videos, or any video content
        on YouTube. It prioritizes video results.

        Args:
            query (str): The search term (e.g., "artist name - song title", "AI explained").
                         Be as specific as possible for best results.
            max_results (int): The maximum number of video results to return. Defaults to 10.
                               The YouTube API limits this to a maximum of 50.
            category_id (str): Optional. The YouTube category ID to filter results.
                               '10' is Music. Set to '' for broader searches.

        Returns:
            List[Dict[str, str]]: A list of dictionaries. Each dictionary contains:
                                  - 'video_id': The YouTube ID of the video.
                                  - 'title': The title of the video.
                                  Returns an empty list if no videos are found or an error occurs.

        Examples:
            >>> youtube_tools.search_video(query="Led Zeppelin Stairway to Heaven official video", max_results=2)
            [
                {'video_id': 'dQw4w9WgXcQ', 'title': 'Led Zeppelin - Stairway To Heaven (Official Audio)'},
                {'video_id': 'another_id', 'title': 'Stairway to Heaven Live (Example)'}
            ]
            >>> youtube_tools.search_video(query="Non-existent video")
            []
        """
        try:
            # Ensure max_results doesn't exceed the YouTube API limit (50)
            effective_max_results = min(max_results, 50)

            search_request_builder = lambda: self.service.search().list(
                part='snippet',
                q=query,
                maxResults=effective_max_results,
                type='video',
                videoCategoryId=category_id if category_id else None
            )

            search_response = self._execute_with_retry(search_request_builder)
            
            # Extract video ID and title for each item
            results = []
            for item in search_response.get('items', []):
                if 'videoId' in item['id']: # Ensure it's a video result
                    results.append({
                        'video_id': item['id']['videoId'],
                        'title': item['snippet']['title']
                    })
            
            return results
        except HttpError as e:
            # For errors, return an empty list and potentially log the error internally
            print(f"Error searching for video '{query}': HTTP Error {e.resp.status} - {e.content.decode()}.")
            return []
        except Exception as e:
            # For unexpected errors, return an empty list and potentially log the error internally
            print(f"An unexpected error occurred while searching for video '{query}': {e}.")
            return []
        
    def create_playlist(self, title: str, description: str = "") -> str:
        """
        Creates a new private YouTube playlist and returns a natural language message
        describing the outcome and details of the created playlist. This playlist
        will initially be empty. To add videos, use the `add_video_to_playlist` tool.

        This tool is useful for setting up a new collection for videos or songs.

        Args:
            title (str): The title of the new playlist.
            description (str): An optional, detailed description for the playlist.
                               Defaults to an empty string.

        Returns:
            str: A natural language message describing the outcome:
                 - Success: "Successfully created new private playlist '{playlist_title}' with ID '{playlist_id}'. This playlist is currently empty. Use the 'add_video_to_playlist' tool to add videos."
                 - Error: "Failed to create playlist '{title}'. An error occurred: [Error details]."

        Examples:
            >>> youtube_tools.create_playlist(
            ...     title="My AI Generated Music Playlist",
            ...     description="A playlist created by an AI based on my preferences."
            ... )
            "Successfully created new private playlist 'My AI Generated Music Playlist' with ID 'PL_new_playlist_id'. This playlist is currently empty. Use the 'add_video_to_playlist' tool to add videos."
        """
        try:
            playlist_request_builder = lambda: self.service.playlists().insert(
                part='snippet,status',
                body={
                    'snippet': {
                        'title': title,
                        'description': description
                    },
                    'status': {
                        'privacyStatus': 'private'
                    }
                }
            )
            playlist_response = self._execute_with_retry(playlist_request_builder)
            playlist_id = playlist_response['id']
            playlist_title = playlist_response['snippet']['title']

            self.latest_playlist_info= {
                 "playlist_ID": playlist_id,
                 "playlist_title": playlist_title,

             }
            self.latests_playlist_videos=[]
            
            return (f"Successfully created new private playlist '{playlist_title}' with ID '{playlist_id}'. "
                    f"This playlist is currently empty. Use the 'add_video_to_playlist' tool to add videos.")

        except HttpError as e:
            return f"Failed to create playlist '{title}'. HTTP Error {e.resp.status} - {e.content.decode()}."
        except Exception as e:
            return f"An unexpected error occurred during playlist creation for '{title}': {e}."

    def add_video_to_playlist(self, playlist_id: str, video_id: str) -> str:
        """
        Adds a single YouTube video to an existing private playlist and returns a
        natural language message describing the outcome.

        This tool allows the AI to populate a playlist created previously or an
        existing one if the playlist ID is known.

        Args:
            playlist_id (str): The ID of the target YouTube playlist.
            video_id (str): The ID of the video to add.

        Returns:
            str: A natural language message describing the outcome:
                 - Success: "Successfully added video '{video_id}' to playlist '{playlist_id}'."
                 - Error: "Failed to add video '{video_id}' to playlist '{playlist_id}'. An error occurred: [Error details]."
                          Specific reasons like 'playlist not found' or 'video already in playlist' are included.

        Examples:
            >>> youtube_tools.add_video_to_playlist(
            ...     playlist_id='PL_your_playlist_id',
            ...     video_id='dQw4w9WgXcQ' # Rick Astley's "Never Gonna Give You Up"
            ... )
            "Successfully added video 'dQw4w9WgXcQ' to playlist 'PL_your_playlist_id'."
            >>> youtube_tools.add_video_to_playlist(
            ...     playlist_id='PL_invalid_id',
            ...     video_id='dQw4w9WgXcQ'
            ... )
            "Failed to add video 'dQw4w9WgXcQ' to playlist 'PL_invalid_id'. An error occurred: HTTP Error 404 - Playlist not found."
        """
        try:
            playlist_item_request_builder = lambda: self.service.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': playlist_id,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': video_id
                        }
                    }
                }
            )
            self._execute_with_retry(playlist_item_request_builder)

            self.latests_playlist_videos.append(video_id)
            
            return f"Successfully added video '{video_id}' to playlist '{playlist_id}'."
        except HttpError as e:
            error_message = e.content.decode()
            reason = ""
            if e.resp.status == 404:
                reason = "Playlist not found or incorrect playlist ID."
            elif e.resp.status == 400 and "duplicate" in error_message.lower():
                reason = "Video might already be in this playlist."
            elif e.resp.status == 403:
                reason = "Insufficient permissions or playlist is not editable."
            
            return f"Failed to add video '{video_id}' to playlist '{playlist_id}'. An error occurred: HTTP Error {e.resp.status} - {error_message}. {reason}".strip()
        except Exception as e:
            return f"An unexpected error occurred while adding video '{video_id}' to playlist '{playlist_id}': {e}."


    def get_summary(self):
            # Accessing playlist_ID and playlist_title
            playlist_id = self.latest_playlist_info.get("playlist_ID")
            playlist_title = self.latest_playlist_info.get("playlist_title")

            # Handle missing playlist info
            if not playlist_id and not playlist_title:
                return "No playlist created yet."

            string_videos = ""
            if self.latests_playlist_videos:
                string_videos = "\nVideos added:\n" + "\n".join(self.latests_playlist_videos)
            else:
                string_videos = "\nNo added videos."

            playlist_info_str = ""
            if playlist_title and playlist_id:
                playlist_info_str = f"Latest playlist created: {playlist_title} with ID: {playlist_id}"
            elif playlist_title:
                playlist_info_str = f"Latest playlist created: {playlist_title} (ID not available)"
            elif playlist_id:
                playlist_info_str = f"Latest playlist created: (Title not available) with ID: {playlist_id}"

            return f"""
    {playlist_info_str}{string_videos}
    """
    


    def open_youtube_item(self, item_id: str, is_playlist: bool = False):
        """
        Opens a YouTube video or playlist in the default web browser.

        Args:
            item_id (str): The ID of the YouTube video or playlist.
            is_playlist (bool): Set to True if the item_id is a playlist ID,
                                False if it's a video ID (default).
        """
        if is_playlist:
            url = f"https://www.youtube.com/playlist?list={item_id}"
        else:
            url = f"https://www.youtube.com/watch?v={item_id}"

        try:
            webbrowser.open_new_tab(url)
            message=f"Opened YouTube {'playlist' if is_playlist else 'video'}: {url}"
            print(message)
            return message
        except webbrowser.Error as e:
            error=f"Error opening URL: {e} \n Please ensure you have a web browser installed and configured."
            print(error)
            return error


# --- IMPORTANT SETUP INSTRUCTIONS FOR THE USER ---
# To use this `YouTubeTools` class, you need to perform the following steps:
#
# 1.  Enable the YouTube Data API v3 in your Google Cloud Project:
#     -   Go to the Google Cloud Console: `console.cloud.google.com`
#     -   Navigate to "APIs & Services" -> "Library".
#     -   Search for "YouTube Data API v3" and click on it.
#     -   Click the "Enable" button.
#
# 2.  Create OAuth 2.0 Client ID Credentials:
#     -   In the Google Cloud Console, go to "APIs & Services" -> "Credentials".
#     -   Click "CREATE CREDENTIALS" -> "OAuth client ID".
#     -   For the "Application type", select "Desktop app".
#     -   Give it a descriptive name (e.g., "YouTube AI Tool").
#     -   Click "CREATE".
#
# 3.  Download the `client_secrets.json` file:
#     -   After creating the credentials, a pop-up will show your client ID and client secret.
#     -   Click the "DOWNLOAD JSON" button.
#     -   Rename the downloaded file to `client_secrets.json` and place it a secret gitignored folder. Currently 'bots/secrets/'.
#          
# 4. Ensure OAuth consent screen and choose scopes inside the Google Cloud Console:
#    - [https://developers.google.com/workspace/guides/configure-oauth-consent]
#    - Set the application name and email on the 'Branding' tab.
#    - Under the 'Audience' tab make sure the user type is set to 'External' and add your email as a test user.
#  
#
# 5.  Install necessary Python libraries:
#     -   Open your terminal or command prompt.
#     -   Run the following command:
#         `pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 google-auth`
#
# Once these steps are completed, you can run the example usage below.
# The first time you run it, a browser window will open, asking you to log in
# to your Google account and grant permissions to the application.
# Subsequent runs will use the `youtube_token.json` file generated into the secret folder specified.
