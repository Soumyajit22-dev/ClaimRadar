import os
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List
from datetime import datetime
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic import Field
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from agents.tools.webcrawl_tool import fetch_site, SiteDoc
from agents.tools.search_tool import search_web, SearchResultItem, SearchResults
from services.neo4j_service import neo4j_service, VerificationResult

# Add the parent directory to the Python path to allow imports from agent_output
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from agents.schema.output import FinalAgentOutput

load_dotenv()
model = OpenAIModel(
    "agentic-large",
    provider=OpenAIProvider(
        base_url="https://api.theagentic.ai/v1", 
        api_key='20WsbU31U3eeo9b8cA2ioICnt0PfCdlw'
    ),
)

@dataclass
class Claim_radar_Deps:
   resources: List[str] = Field(..., description="User recommended trusted sites, on which user trust that their results are always true")
   

class Claimradar_agent:
    def __init__(self, model = model):
        self.model = model


    def _read_markdown_file(self, file_path: str) -> str:
        """Read and return content of markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
        

    async def agent(self, system_prompt: str)-> Agent:
        agent = Agent(
            model=self.model,
            system_prompt= system_prompt,
            deps_type = Claim_radar_Deps,
            output_type=FinalAgentOutput 
        )
        @agent.tool
        def fetch_site_tool(url: str) -> SiteDoc:
            """Tool the agent can call. Returns typed SiteDoc."""
            return fetch_site(url)
        @agent.tool
        def search_tool(query: str, limit: int = 5) -> SearchResults:
            """Tool: run a web search and return typed SearchResults (urls + snippets)."""
            try:
                raw = search_web(query, limit=limit)
                items = [SearchResultItem(url=r["url"], title=r.get("title"), snippet=r.get("snippet")) for r in raw]
                return SearchResults(query=query, results=items)
            except Exception as e:
                raise RuntimeError(f"search_tool failed: {e}")
        
        return agent
    
    async def claim_verifier(self, ctx: RunContext[Claim_radar_Deps], resources: List[str], sensitivity:int, input_id: str, md_path: str):
        
        try:
            # Read the markdown content for caching
            markdown_content = self._read_markdown_file(md_path)
            
            # Check for exact match first (same text hash)
            text_hash = neo4j_service.calculate_text_hash(markdown_content)
            cached_result = neo4j_service.get_verification_by_hash(text_hash)
            
            if cached_result:
                print(f"🎯 Found exact match for {input_id} - returning cached result")
                return cached_result
            
            # Extract keywords for similarity matching
            keywords = neo4j_service.extract_keywords(markdown_content)
            
            # Check for similar content (70%+ keyword overlap)
            similar_results = neo4j_service.find_similar_verifications(keywords, threshold=0.7)
            
            if similar_results:
                best_match = similar_results[0]  # Highest similarity
                print(f"🎯 Found similar content ({best_match['similarity']:.2%} match) for {input_id} - returning cached result")
                return best_match
            
            print(f"🔄 No cached result found for {input_id} - running agent verification")
            
            ctx.deps.resources = resources
            system_prompt = """
You are a specialized fact-checker and misinformation detection agent focused exclusively on global crises domains. Your role is to verify the accuracy of information related to pandemics, geopolitical conflicts, and climate events by conducting comprehensive research using web search and site crawling tools.
## Domain Scope:
You ONLY fact-check content related to these three critical domains:
1. **Global crises like pandemics**: Disease outbreaks, public health emergencies, vaccine information, health policies, epidemiological data
2. **Geopolitical Conflicts**: Wars, international tensions, diplomatic relations, military actions, territorial disputes, sanctions
3. **Climate Events**: Climate change impacts, natural disasters, environmental policies, carbon emissions, weather patterns, environmental science

## Tool Usage Instructions:

### 1. Search Tool Usage:
- **Function**: `search_tool(query: str, limit: int = 5)`
- **Parameters**:
  - `query`: Search string with relevant keywords for the claim you're verifying
  - `limit`: Maximum number of results to return (default: 5, max recommended: 10)
- **Returns**: `SearchResults` object containing:
  - `query`: The search query used
  - `results`: List of `SearchResultItem` objects with:
    - `url`: URL of the source
    - `title`: Title of the article/page
    - `snippet`: Brief description/snippet
- **Usage Examples**:
  - `search_tool("COVID-19 vaccine effectiveness 2024", 8)`
  - `search_tool("Ukraine war casualties statistics", 5)`
  - `search_tool("climate change temperature rise IPCC", 6)`

### 2. Fetch Site Tool Usage:
- **Function**: `fetch_site_tool(url: str)`
- **Parameters**:
  - `url`: Complete URL of the webpage to crawl and analyze
- **Returns**: `SiteDoc` object containing:
  - `source_url`: The URL that was crawled
  - `title`: Page title
  - `markdown`: Full content in markdown format
  - `fetched_at`: Timestamp of when content was fetched
  - `metadata`: Additional page metadata
- **Usage Examples**:
  - `fetch_site_tool("https://www.who.int/news-room/fact-sheets/detail/covid-19")`
  - `fetch_site_tool("https://www.un.org/en/climatechange/reports")`
  - `fetch_site_tool("https://www.reuters.com/world/ukraine-conflict/")`

### 3. User-Trusted Resources:
- **Access**: Available through `ctx.deps.resources` (List[str])
- **Usage**: These are URLs the user specifically trusts - prioritize these sources
- **Process**: Use `fetch_site_tool` to crawl these URLs for detailed content
- **Example**: If `ctx.deps.resources = ["https://reuters.com", "https://bbc.com"]`, crawl these first

## Your Process:
1. **Domain Assessment**: First, determine if the input content falls within any of the three domains listed above.

2. **Out-of-Domain Handling**: If the content is NOT related to Global crises like pandemics, geopolitical conflicts, or climate events:
   - Return: `Correctness: true`
   - Return: `Out_of_domain: true`
   - Return: `misinfo: "N/A - Content is outside the scope of global crises domains (Global crises like pandemics, geopolitical conflicts, climate events). No misinformation assessment applicable."`
   - Return: `rightinfo: "N/A - Content outside verification scope"`
   - Return: `confidence_score: "1.0"`
   - Return: `sources: []`

3. **In-Domain Verification**: If content IS related to the defined Domains:
   - **Step 1**: Use `search_tool` with domain-specific keywords to find relevant sources
   - **Step 2**: Use `fetch_site_tool` to crawl the most relevant URLs from search results
   - **Step 3**: Prioritize crawling URLs from `ctx.deps.resources` using `fetch_site_tool`
   - **Step 4**: Cross-reference information from multiple sources
   - **Step 5**: Identify any contradictions or conflicting information

## Data Collection and Analysis:
- **From Search Results**: Extract URLs, titles, and snippets for initial assessment
- **From Crawled Content**: Analyze full markdown content for detailed verification
- **From User-Trusted Sources**: Give higher weight to information from `ctx.deps.resources`
- **Cross-Reference**: Compare findings across multiple sources to establish accuracy

## Output Requirements:
For domain-relevant content, provide a structured response with:

- **Correctness**: bool - True if the information is accurate and verified, False if it contains misinformation or cannot be verified
- **Out_of_domain**: bool - True if content is outside the defined domains, False if within scope
- **misinfo**: str - If misinformation is found, clearly describe what specific false information is present in the input
- **rightinfo**: str - If misinformation is found, provide the correct, verified information that should replace the misinformation
- **confidence_score**: str - A score from "0.0" to "1.0" indicating your confidence in the verification ("1.0" = very confident, "0.0" = uncertain)
- **sources**: List[str] - List of URLs and source names that support your verification findings

## Guidelines:
- ONLY process content related to Global crises like pandemics, geopolitical conflicts, or climate events
- For out-of-domain content, return correctness: true with appropriate messaging
- Use domain-specific search strategies and keywords
- Always crawl relevant URLs using `fetch_site_tool` for detailed analysis
- Prioritize user-trusted resources from `ctx.deps.resources`
- Be thorough in cross-referencing multiple sources
- Distinguish between verified facts and opinions
- Always cite your sources with specific URLs
- Be objective and evidence-based in your assessments
- If multiple sources contradict each other, note this in your analysis
"""

            user_input = f"Here is the markdown file content to fact-check: {markdown_content}"
            print("passed input..")
            agent = await self.agent(system_prompt=system_prompt)
            try:
                response = await agent.run(user_input, deps=ctx.deps)
                print("agent called..")
                # Save response to JSON file
                response_data = response.output
                
                # Store in Neo4j for future caching
                verification_result = VerificationResult(
                    input_id=input_id,
                    keywords=keywords,
                    correctness=response_data.correctness,
                    out_of_domain=response_data.out_of_domain,
                    misinfo=response_data.misinfo,
                    rightinfo=response_data.rightinfo,
                    confidence_score=response_data.confidence_score,
                    sources=response_data.sources,
                    created_at=datetime.now(),
                    raw_text_hash=text_hash
                )
                
                # Store in Neo4j
                neo4j_service.store_verification(verification_result)
                
                # Save response to JSON file (backup)
                responses_dir = os.path.join(parent_dir, "responses")
                os.makedirs(responses_dir, exist_ok=True)
                
                output_path = f'{input_id}_verification.json'
                full_output_path = os.path.join(responses_dir, output_path)
                
                with open(full_output_path, 'w') as f:
                    json.dump(response_data.model_dump(), f, indent=2)
                
                print(f"Saved verification response to: {full_output_path}")
                return response_data
                
            except Exception as e:
                print(f"Error with agent run: {e}")
                raise ValueError(f"Failed to process document: {str(e)}")
            
        except Exception as e:
            raise ValueError(f"Failed to save response file: {str(e)}")
        