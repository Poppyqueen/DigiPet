import requests
import time
wiki_url = "https://en.wikipedia.org/w/api.php"

random_params = {
    "action": "query",
    "list": "random",
    "rnnamespace": "0",
    "rnlimit": "1",
    "format": "json"
}

# Removed format_remaining_time function

# --- Function to fetch random wiki data ---
def fetch_random_wiki_article():
    """
    Fetches a random Wikipedia page title and its content.
    Returns a structured string with title and body.
    """
    page_title = "Error: Title not fetched"
    page_extract = "Error: Content not fetched"

    # Removed cache-related initializations and prints

    try:
        # Step 1: Get a random page title using standard requests
        # Removed timing and cache status prints
        response_title = requests.get(wiki_url, params=random_params)
        response_title.raise_for_status() # Raise an exception for bad status codes

        random_data = response_title.json()

        if 'query' in random_data and 'random' in random_data['query'] and random_data['query']['random']:
            page_title = random_data['query']['random'][0]['title']
        else:
            raise ValueError("Failed to get random page title from API response")

        # Step 2: Get content for the page using standard requests
        content_params = {
            "action": "query",
            "titles": page_title,
            "prop": "extracts",
            "explaintext": 1,
            "exlimit": 1,
            "format": "json"
        }

        # Removed timing and cache status prints
        response_content = requests.get(wiki_url, params=content_params)
        response_content.raise_for_status() # Raise an exception for bad status codes

        content_data = response_content.json()

        if 'query' in content_data and 'pages' in content_data['query']:
             # Get the page ID (which is the key under 'pages')
            page_id = next(iter(content_data['query']['pages']))
            # Check if the page_id is -1, which can happen for ambiguous titles
            if page_id == '-1':
                 page_extract = f"Could not retrieve content for page '{page_title}' (Page not found or ambiguous)."
            else:
                page_extract = content_data['query']['pages'][page_id].get('extract', 'No text extract available for this page.')
        else:
            page_extract = "Error: Could not retrieve page content from API response structure."

    except requests.exceptions.RequestException as e:
        # Handle network errors or bad HTTP responses
        page_title = f"Error fetching data: {e}"
        page_extract = "Failed to connect to Wikipedia API or received an error response."
    except ValueError as e:
        # Handle JSON parsing errors or unexpected data structure
        page_title = f"Error processing data: {e}"
        page_extract = "Received unexpected data format from API."
    except Exception as e:
        # Catch any other unexpected errors
        page_title = f"An unexpected error occurred: {e}"
        page_extract = "An unknown error occurred during fetch or processing."

    # Structure the output string
    structured_string = f"Title: {page_title}\n\nBody:\n{page_extract}"

    # Removed the final message that included cache status
    time.sleep(1)
    return structured_string # Return only the structured string
