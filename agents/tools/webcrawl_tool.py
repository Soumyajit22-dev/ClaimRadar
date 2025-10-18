import os
from typing import Optional, Dict, Any
from pydantic import BaseModel

try:
    from firecrawl import FirecrawlApp
except ImportError:
    # Fallback for different firecrawl package versions
    try:
        from firecrawl import Firecrawl
    except ImportError:
        FirecrawlApp = None
        Firecrawl = None

class SiteDoc(BaseModel):
    source_url: str = None
    title: Optional[str] = None
    markdown: str = None
    fetched_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# 2) Firecrawl client initialization
def _get_firecrawl_client():
    """Initialize Firecrawl client with fallback for different package versions"""
    api_key = os.environ.get("FIRECRAWL_API_KEY", "your-firecrawl-key")
    
    if FirecrawlApp is not None:
        return FirecrawlApp(api_key=api_key)
    elif Firecrawl is not None:
        return Firecrawl(api_key=api_key)
    else:
        raise ImportError("Firecrawl package not found. Please install with: pip install firecrawl-py")

# 3) helper that calls Firecrawl and returns validated model
def fetch_site(url: str, formats: list[str] = ["markdown"]) -> SiteDoc:
    try:
        fc = _get_firecrawl_client()
        # Firecrawl SDK: scrape returns a dict-like result (see docs)
        res = fc.scrape(url, formats=formats)
        
        # extract fields safely (structure depends on requested formats)
        # typical keys: 'markdown', 'metadata' etc. Adjust as needed.
        doc = {
            "source_url": res.get("url") or url,
            "title": (res.get("title") or None),
            "markdown": res.get("markdown") or res.get("html") or "",
            "fetched_at": res.get("fetched_at") if "fetched_at" in res else None,
            "metadata": res.get("metadata") or None,
        }
        return SiteDoc.model_validate(doc)
    except Exception as e:
        # Return a basic SiteDoc with error information
        return SiteDoc(
            source_url=url,
            title="Error",
            markdown=f"Error fetching site: {str(e)}",
            fetched_at=None,
            metadata={"error": str(e)}
        )