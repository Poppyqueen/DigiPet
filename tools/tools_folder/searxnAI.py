import requests
import json
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import trafilatura
from datetime import datetime, timedelta

from dotenv import load_dotenv
import os


load_dotenv()

# Configuration
SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL")


CACHE_EXPIRY_HOURS = 24

@dataclass
class SearchResult:
    """Structured search result with unique ID"""
    id: str
    title: str
    url: str
    snippet: str
    timestamp: str

class AISearXNG:
    """
    Agentic search system with controlled web access.
    
    Design Principles:
    - Structured natural language outputs
    - Simple arguments
    - Paginated search (max 10 results)
    - Cached content retrieval via IDs
    - No arbitrary web requests
    """
    
    def __init__(self):
        self.base_url = SEARXNG_BASE_URL
        self.search_cache: Dict[str, SearchResult] = {}
        self.content_cache: Dict[str, Dict] = {}
        
    def _generate_result_id(self, url: str) -> str:
        """Generate deterministic unique ID from URL"""
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    def _is_cache_valid(self, timestamp_str: str) -> bool:
        """Check if cached content is still valid"""
        try:
            cached_time = datetime.fromisoformat(timestamp_str)
            return datetime.now() - cached_time < timedelta(hours=CACHE_EXPIRY_HOURS)
        except:
            return False
    
    def _fetch_clean_content(self, url: str) -> Optional[str]:
        """
        Fetch and extract clean text from URL using trafilatura.
        Returns cached content if available and valid.
        """
        result_id = self._generate_result_id(url)
        
        # Check content cache first
        if result_id in self.content_cache:
            cached = self.content_cache[result_id]
            if self._is_cache_valid(cached['timestamp']):
                return cached['content']
        
        try:
            # Fetch and extract with trafilatura
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None
                
            clean_text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )
            
            # Cache the content
            if clean_text:
                self.content_cache[result_id] = {
                    'content': clean_text,
                    'url': url,
                    'timestamp': datetime.now().isoformat()
                }
            
            return clean_text
        except Exception as e:
            return f"Error fetching content: {str(e)}"
    
    def search(self, query: str, page: int = 1, max_results: int = 20) -> str:
        """
        Search SearXNG and return formatted results with IDs.
        
        Args:
            query: Search query string
            page: Page number (default: 1)
            max_results: Maximum results to return (default: 20, max: 20)
        
        Returns:
            Natural language formatted search results with IDs for retrieval
        """
        max_results = min(max_results, 20)  # Enforce max limit
        
        params = {
            'q': query,
            'format': 'json',
            'pageno': page
        }
        
        try:
            response = requests.get(f"{self.base_url}/", params=params, timeout=10)
            response.raise_for_status()
            results_json = response.json()
            
            if not results_json.get('results'):
                return f"No results found for query: '{query}'"
            
            # Process and cache results
            output_lines = [
                f"Search Results for: '{query}'",
                f"Page {page} | Showing up to {max_results} results",
                "=" * 60,
                ""
            ]
            
            for idx, result in enumerate(results_json['results'][:max_results], 1):
                url = result.get('url', '')
                result_id = self._generate_result_id(url)
                
                # Create and cache search result
                search_result = SearchResult(
                    id=result_id,
                    title=result.get('title', 'No title'),
                    url=url,
                    snippet=result.get('content', 'No description available')[:200],
                    timestamp=datetime.now().isoformat()
                )
                self.search_cache[result_id] = search_result
                
                # Format output
                output_lines.extend([
                    f"[{idx}] ID: {result_id}",
                    f"    Title: {search_result.title}",
                    f"    URL: {search_result.url}",
                    f"    Snippet: {search_result.snippet}...",
                    ""
                ])
            
            output_lines.append(f"\nTo read full content, use: query_website(ID)")
            return "\n".join(output_lines)
            
        except requests.exceptions.Timeout:
            return f"Search request timed out for query: '{query}'"
        except requests.exceptions.RequestException as e:
            return f"Search error: {str(e)}"
    
    def query_website(self, result_id: str) -> str:
        """
        Retrieve full content of a cached search result by ID.
        
        Args:
            result_id: The ID from search results
        
        Returns:
            Natural language formatted full page content
        """
        # Check if ID exists in search cache
        if result_id not in self.search_cache:
            return (
                f"Error: ID '{result_id}' not found in search cache.\n"
                "Please perform a search first to get valid IDs."
            )
        
        search_result = self.search_cache[result_id]
        
        # Fetch clean content
        output_lines = [
            f"Content for: {search_result.title}",
            f"URL: {search_result.url}",
            f"ID: {result_id}",
            "=" * 60,
            "",
            "Fetching full content...",
            ""
        ]
        
        content = self._fetch_clean_content(search_result.url)
        
        if content:
            output_lines.append(content)
            return "\n".join(output_lines)
        else:
            return "\n".join(output_lines[:-2]) + "\n\nError: Could not extract content from this page."
    
    def get_cached_result(self, result_id: str) -> Optional[Dict]:
        """Get cached search result metadata by ID"""
        if result_id in self.search_cache:
            return asdict(self.search_cache[result_id])
        return None
    
    def list_cache(self, pagination: int = 1) -> str:
        """List all cached search results"""
        if not self.search_cache:
            return "Cache is empty. Perform a search first."
        
        output_lines = [
            "Cached Search Results",
            "=" * 60,
            ""
        ]

        max_results = min(pagination * 20, len(self.search_cache))
        
        for result_id, result in self.search_cache.items()[:max_results]:
            output_lines.extend([
                f"ID: {result_id}",
                f"Title: {result.title}",
                f"URL: {result.url}",
                f"Cached: {result.timestamp}",
                ""
            ])
        
        return "\n".join(output_lines)


# Usage Example
if __name__ == "__main__":
    # Initialize the agent
    agent = AISearXNG()
    
    # Example 1: Search for something
    print("=== EXAMPLE 1: Search ===")
    search_output = agent.search("Python web scraping")
    print(search_output)
    
    print("\n\n=== EXAMPLE 2: Query Website ===")
    # Extract first ID from search results (in practice, agent would parse this)
    # For demo, we'll manually get it
    if agent.search_cache:
        first_id = list(agent.search_cache.keys())[0]
        content_output = agent.query_website(first_id)
        print(content_output[:1000] + "...")  # Print first 1000 chars
    
    print("\n\n=== EXAMPLE 3: List Cache ===")
    cache_output = agent.list_cache()
    print(cache_output)