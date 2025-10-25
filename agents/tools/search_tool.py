import os
import requests
import json
from typing import Optional, List, Dict
from pydantic import BaseModel
from configs.config import get_settings

class SearchResultItem(BaseModel):
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None

class SearchResults(BaseModel):
    query: str
    results: List[SearchResultItem]

def search_web(query: str, limit: int = 5) -> List[Dict]:
    """
    Search the web using Serper API.
    Returns a list of dicts with 'url', 'title', and 'snippet' keys.
    """
    settings = get_settings()
    api_key = settings.api_keys.serp_api_key.get_secret_value()
    
    if not api_key or api_key == "SERP_API_KEY":
        print("Warning: Serper API key not configured. Returning empty results.")
        return []
    
    # Serper API endpoint
    url = "https://google.serper.dev/search"
    
    # Request headers
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    # Request payload
    payload = {
        'q': query,
        'num': min(limit, 10)  # Serper API max is 10
    }
    
    try:
        # Make the API request
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        # Extract search results
        results = []
        organic_results = data.get('organic', [])
        
        for result in organic_results[:limit]:
            search_item = {
                'url': result.get('link', ''),
                'title': result.get('title', ''),
                'snippet': result.get('snippet', '')
            }
            results.append(search_item)
        
        print(f"✅ Serper API search successful: Found {len(results)} results for query: '{query}'")
        return results
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Serper API request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse Serper API response: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error during search: {e}")
        return []