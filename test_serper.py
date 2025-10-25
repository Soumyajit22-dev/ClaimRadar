#!/usr/bin/env python3
"""
Test script to demonstrate Serper API usage
"""

import sys
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from agents.tools.search_tool import search_web, SearchResults, SearchResultItem

def test_serper_api():
    """Test the Serper API implementation"""
    print("🔍 Testing Serper API Integration")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        "COVID-19 vaccine effectiveness 2024",
        "Ukraine war latest news",
        "climate change temperature rise"
    ]
    
    for query in test_queries:
        print(f"\n🔎 Searching for: '{query}'")
        print("-" * 30)
        
        try:
            # Perform search
            results = search_web(query, limit=3)
            
            if results:
                print(f"✅ Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. {result.get('title', 'No title')}")
                    print(f"   URL: {result.get('url', 'No URL')}")
                    print(f"   Snippet: {result.get('snippet', 'No snippet')[:100]}...")
            else:
                print("❌ No results found")
                
        except Exception as e:
            print(f"❌ Error during search: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

def test_search_results_class():
    """Test the SearchResults class usage"""
    print("\n🧪 Testing SearchResults Class")
    print("=" * 50)
    
    # Create sample search results
    sample_results = [
        SearchResultItem(
            url="https://example.com/article1",
            title="Sample Article 1",
            snippet="This is a sample snippet for testing purposes."
        ),
        SearchResultItem(
            url="https://example.com/article2", 
            title="Sample Article 2",
            snippet="Another sample snippet for demonstration."
        )
    ]
    
    # Create SearchResults object
    search_results = SearchResults(
        query="test query",
        results=sample_results
    )
    
    print(f"Query: {search_results.query}")
    print(f"Number of results: {len(search_results.results)}")
    
    for i, result in enumerate(search_results.results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   URL: {result.url}")
        print(f"   Snippet: {result.snippet}")

if __name__ == "__main__":
    # Test the SearchResults class first
    test_search_results_class()
    
    # Test the actual Serper API
    test_serper_api()
