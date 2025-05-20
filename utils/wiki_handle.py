import requests
import time
import textwrap  # Helps wrap long text snippets nicely
import re        # Import regular expressions for tag stripping
import html      # Import html module for entity decoding

#import tokens_handle

wiki_url = "https://en.wikipedia.org/w/api.php"

class Wikipedia_handle:
    """
    A class to handle Wikipedia API operations including searching, retrieving content,
    and fetching random articles, with built-in memory management.
    """

    def __init__(self, memory_manager):
        self.memory = memory_manager

    def _call_wiki_api(self, params: dict) -> dict:
        """
        Makes a call to the Wikipedia API with given parameters.

        Args:
            params: A dictionary of API parameters.

        Returns:
            A dictionary containing the JSON response from the API.

        Raises:
            requests.exceptions.RequestException: If there's a network error or bad HTTP status code.
            ValueError: If the API response is not valid JSON.
            Exception: For other unexpected errors.
        """
        # Ensure the format is always JSON for consistency
        params['format'] = 'json'

        # Add a user agent string - recommended practice for APIs
        headers = {
            'User-Agent': 'YourAppName/1.0 (Your Contact Info or purpose here)'  # User-Agent is from your last version
        }

        try:
            # print(f"Calling API with params: {params}")  # Optional: for debugging
            response = requests.get(wiki_url, params=params, headers=headers)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            # Good practice: sleep *after* the successful call to respect API rate limits
            # Adjust the sleep duration if needed, but 1 second is usually safe.
            time.sleep(1)

            return response.json()

        except requests.exceptions.RequestException as e:
            # print(f"API Request Error: {e}")  # Helper prints, main functions will format
            # Re-raise the exception so calling functions can handle it
            raise
        except ValueError as e:
            # print(f"API JSON Parsing Error: {e}")  # Helper prints, main functions will format
            # Re-raise the exception if JSON is invalid
            raise
        except Exception as e:
            # print(f"An unexpected error occurred during API call: {e}")  # Helper prints, main functions will format
            # Re-raise any other unexpected errors
            raise

    def _clean_html(self, text: str) -> str:
        """
        Removes simple HTML tags and decodes HTML entities from a string.
        Specifically targets <span class="searchmatch">...</span> tags found
        in Wikipedia search snippets, but uses a general tag stripping regex.
        It also decodes common HTML entities.
        """
        if not isinstance(text, str):
            return text  # Return non-string input as is

        # Decode HTML entities (like ", ', &)
        cleaned_text = html.unescape(text)
        # Remove simple HTML tags (e.g., <span ...>, </span>)
        # This regex removes anything that looks like an HTML tag <...>
        cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)

        # Handle potential list item markers that might remain if explaintext isn't perfect
        # (Though this might be less relevant for search snippets)
        cleaned_text = re.sub(r'^\* ', '- ', cleaned_text, flags=re.MULTILINE)  # Convert * to - for lists
        cleaned_text = re.sub(r'^: ', '  ', cleaned_text, flags=re.MULTILINE)  # Indent definition lists

        return cleaned_text

    def search_wikipedia(self, query: str) -> str:
        """
        Searches Wikipedia for a term and returns a formatted string of potential
        page titles with cleaned snippets.

        Args:
            query: The search term string.

        Returns:
            A formatted string listing the search results (title and cleaned snippet),
            or a string indicating no results were found, or an error message.
        """
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srprop": "snippet|pageid",  # Request snippet and page ID
            "srlimit": 10,               # Increase limit slightly for more options
            # format is added by the helper
        }

        output_string_parts = []

        try:
            data = self._call_wiki_api(search_params)

            # Check if 'query' and 'search' are in the response structure and search list is not empty
            if 'query' in data and 'search' in data['query'] and data['query']['search']:
                search_results = data['query']['search']
                output_string_parts.append(f"Search results for '{query}':\n")
                output_string_parts.append("------------------------------\n")

                for i, item in enumerate(search_results):
                    title = item.get('title', 'N/A')
                    snippet = item.get('snippet', 'No snippet available')

                    # *** CLEAN THE SNIPPET using the new helper ***
                    cleaned_snippet = self._clean_html(snippet)

                    # Let's wrap the cleaned snippet nicely
                    wrapped_lines = textwrap.wrap(cleaned_snippet, width=80)
                    # Join with newline and indentation for subsequent lines
                    wrapped_snippet_indented = "\n    ".join(wrapped_lines)

                    output_string_parts.append(f"{i+1}. Title: {title}\n")
                    output_string_parts.append(f"   Snippet: {wrapped_snippet_indented}...\n")  # Add ... to indicate it's a snippet
                    output_string_parts.append("-" * 10 + "\n")  # Separator for each result

                output_string_parts.append(f"Total results found: {len(search_results)}\n")

            elif 'query' in data and 'search' in data['query'] and not data['query']['search']:
                # 'search' key exists but the list is empty
                output_string_parts.append(f"No search results found for '{query}'. Please try another query.")

            else:
                # This might happen if the API structure changes unexpectedly or is weirdly empty
                print(f"Warning: Unexpected API search response structure for query '{query}': {data}")
                output_string_parts.append(f"Error: Could not parse search results for '{query}'. Unexpected API response.")

        except (requests.exceptions.RequestException, ValueError) as e:
            # Catch exceptions raised by _call_wiki_api or parsing errors here
            print(f"Error in search_wikipedia for query '{query}': {e}")  # Print error for logging/debugging
            # Return a user-friendly error message string
            output_string_parts.append(f"An API or parsing error occurred while searching for '{query}': {e}")
        except Exception as e:
            # Catch any other unexpected errors
            print(f"An unexpected error occurred during search for '{query}': {e}")
            output_string_parts.append(f"An unexpected error occurred during search for '{query}': {e}")

        return "".join(output_string_parts)  # Join all parts into a single string

    def _get_wikipedia_excerpt(self, title: str) -> str:
        """
        Fetches a shorter excerpt for a Wikipedia page by title.
        Used when memory constraints are reached.

        Args:
            title: The exact title of the Wikipedia page.

        Returns:
            A string containing the excerpt of the article,
            or an error message if content cannot be retrieved.
        """
        excerpt_params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": 1,      # Get only the intro section
            "explaintext": 1,  # Get plain text
            "exlimit": 1,      # Get only one extract
            "redirects": 1,    # Follow redirects
            # format is added by the helper
        }

        try:
            data = self._call_wiki_api(excerpt_params)

            # Navigate the complex pages structure
            if 'query' in data and 'pages' in data['query']:
                # The page ID is the key under 'pages'. Get the first (and likely only) one.
                page_id = next(iter(data['query']['pages']))
                page_data = data['query']['pages'][page_id]

                # Check if the page ID is -1, which means the page was not found
                if page_id == '-1':
                    return f"Wikipedia page '{title}' not found or ambiguous."
                else:
                    # Page found, extract the introduction
                    page_title = page_data.get('title', title)  # Use fetched title if available
                    extract = page_data.get('extract', '')
                    
                    if not extract:
                        return f"No excerpt available for page '{page_title}'."
                    else:
                        return extract

            else:
                return f"Error: Could not parse excerpt response for '{title}'. Unexpected API response."

        except Exception as e:
            return f"An error occurred while fetching excerpt for '{title}': {e}"

    def get_wikipedia_content_by_title(self, title: str) -> str:
        """
        Fetches the content extract for a specific Wikipedia page by title.
        Checks memory constraints and provides full content or excerpt as appropriate.

        Args:
            title: The exact title of the Wikipedia page.

        Returns:
            A structured string containing the Title and Body of the article extract,
            or a structured string indicating an error if the page is not found
            or content cannot be retrieved.
        """
        # First check memory constraints to determine if we should fetch full content or just excerpt
        mem_tokens = self.memory.current_memory_tokens()
        use_excerpt_only = mem_tokens >= 400,000

        content_params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": 1,  # Get plain text
            "exlimit": 1,      # Get only one extract (should be 1 for a specific title)
            "redirects": 1,    # Follow redirects
            "uselang": "en",   # Ensure English language content
            # format is added by the helper
        }

        page_title_output = title  # Default title for output, updated if found
        page_extract_output = f"Attempted to retrieve content for '{title}'..."  # Initial state

        try:
            # If memory constraints are high, use the excerpt method directly
            if use_excerpt_only:
                page_extract_output = self._get_wikipedia_excerpt(title)
                # Note: we don't have the actual title here, so we'll use the original title
            else:
                # Normal full content fetch
                data = self._call_wiki_api(content_params)

                # Navigate the complex pages structure
                if 'query' in data and 'pages' in data['query']:
                    # The page ID is the key under 'pages'. Get the first (and likely only) one.
                    # Handle potential redirects where the title might change
                    page_id = next(iter(data['query']['pages']))
                    page_data = data['query']['pages'][page_id]

                    # Check if the page ID is -1, which means the page was not found or ambiguous
                    if page_id == '-1':
                        page_extract_output = f"Wikipedia page '{title}' not found or ambiguous."
                        # page_title_output remains the original query title in this case
                    else:
                        # Page found, extract the data
                        page_title_output = page_data.get('title', title)  # Use fetched title if available
                        # Get the extract, default to a message if not present or empty
                        extract = page_data.get('extract', '')
                        if not extract:
                            page_extract_output = f"No text extract available for page '{page_title_output}'."
                        else:
                            # Extract found, set it (NOT CLEANED)
                            page_extract_output = extract

                else:
                    # Unexpected data structure from API
                    print(f"Warning: Unexpected API content response structure for title '{title}': {data}")
                    page_extract_output = f"Error: Could not parse content response for '{title}'. Unexpected API response."

        except (requests.exceptions.RequestException, ValueError) as e:
            # Catch exceptions raised by _call_wiki_api or parsing errors here
            print(f"Error in get_wikipedia_content_by_title for title '{title}': {e}")  # Print error for logging/debugging
            # *** The error message will NOT be cleaned before embedding in the string ***
            page_extract_output = f"An API or parsing error occurred while fetching content for '{title}': {e}"
        except Exception as e:
            # Catch any other unexpected errors
            print(f"An unexpected error occurred during content fetch for '{title}': {e}")  # Print error for logging/debugging
            # *** The error message will NOT be cleaned before embedding in the string ***
            page_extract_output = f"An unexpected error occurred during content fetch for '{title}': {e}"

        # Include note about excerpt usage if memory constraints triggered it
        content_note = "(EXCERPT ONLY - Memory constraints reached)" if use_excerpt_only else ""

        # Structure the output string consistently, with clear separation
        structured_string = f"""
TITLE: {page_title_output} {content_note}
BODY:
{page_extract_output}
"""

        return structured_string

    def fetch_random_wiki_article(self) -> str:
        """
        Fetches a random Wikipedia page title and its content.
        Checks memory constraints before retrieving full content.
        
        Returns:
            A structured string with title and body, or an error message string.
        """
        # Check memory constraints first
        mem_tokens = self.memory.current_memory_tokens()
        use_excerpt_only = mem_tokens >= 600000

        random_params = {
            "action": "query",
            "list": "random",
            "rnnamespace": "0",  # Limit to main articles
            "rnlimit": "1",
            # format is added by the helper
        }

        try:
            # Step 1: Get a random page title using the helper
            data_title = self._call_wiki_api(random_params)

            page_title = None
            if 'query' in data_title and 'random' in data_title['query'] and data_title['query']['random']:
                page_title = data_title['query']['random'][0]['title']
            else:
                # If we couldn't get a random title, raise an error to be caught below
                raise ValueError("Failed to get random page title from API response.")  # Data structure error

            # Step 2: Get content for the page using the helper function
            # The get_wikipedia_content_by_title function now handles memory constraints
            if page_title:
                return self.get_wikipedia_content_by_title(page_title)
            else:
                # This case should ideally be covered by the ValueError above, but as a fallback
                raise ValueError("Could not determine a random page title to fetch content for.")

        except (requests.exceptions.RequestException, ValueError) as e:
            # Catch errors from the helper or the data parsing above during title fetch
            print(f"Error in fetch_random_wiki_article (during title fetch): {e}")  # Print error for logging/debugging
            # Return a structured error string consistent with get_wikipedia_content_by_title
            structured_error = f"""
TITLE: Error Fetching Random Article
BODY:
Failed to fetch a random article title: {e}
"""
            return structured_error
        except Exception as e:
            # Catch any other unexpected errors during the random fetch logic
            print(f"An unexpected error occurred during random fetch: {e}")  # Print error for logging/debugging
            structured_error = f"""
TITLE: Unexpected Error
BODY:
An unexpected error occurred while fetching a random article: {e}
"""
            return structured_error