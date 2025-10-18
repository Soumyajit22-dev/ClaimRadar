import os
import requests
from typing import Optional, List, Dict
from pydantic import BaseModel


class SearchResultItem(BaseModel):
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None

class SearchResults(BaseModel):
    query: str
    results: List[SearchResultItem]

# Get API key from environment
SEARCH_API_KEY = os.getenv("SERPAPI_API_KEY", "serp-YOUR-API-KEY")

def search_web(query: str, limit: int = 5) -> List[Dict]:
    """
    Minimal synchronous search wrapper.
    Replace the requests.get(...) below with SerpAPI, Bing, or your preferred provider.
    The function returns a list of dicts like {'url','title','snippet'}.
    """
    if not SEARCH_API_KEY or SEARCH_API_KEY.startswith("serp-YOUR"):
        # No-key fallback: return empty so agent sees search returned nothing.
        return []

    # Example (placeholder) - adapt to your vendor API (SerpAPI/Bing etc.)
    endpoint = "https://serpapi.example/search.json"  # <- REPLACE
    params = {"q": query, "api_key": SEARCH_API_KEY, "num": limit}
    resp = requests.get(endpoint, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for r in data.get("organic_results", [])[:limit]:
        url = r.get("link") or r.get("url")
        title = r.get("title") or r.get("result_title")
        snippet = r.get("snippet") or r.get("description")
        if url:
            results.append({"url": url, "title": title, "snippet": snippet})
    return results