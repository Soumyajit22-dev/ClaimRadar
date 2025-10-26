from pydantic_ai import Agent, RunContext
from pydantic import Field, BaseModel
from pydantic_ai.usage import Usage
from pydantic_ai.models.openai import OpenAIModel
from dataclasses import dataclass
from typing import List
from datetime import datetime
import os, json
from pathlib import Path
from models.base import get_model

from agents.tools.webcrawl_tool import fetch_site, SiteDoc
from agents.tools.search_tool import search_web, SearchResultItem, SearchResults
from agents.schema.output import FinalAgentOutput

model, model_settings = get_model()


class Claim_radar_Deps(BaseModel):
    resources: List[str] = Field(..., description="User-trusted resource URLs for fact-checking")


class Claimradar_agent:
    def __init__(self, model=model, m=model_settings):
        self.model = model
        self.m = m

    def _read_markdown_file(self, file_path: str) -> str:
        """Read markdown file safely."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            raise RuntimeError(f"Error reading file: {e}")

    async def _create_context(self, resources: List[str]) -> RunContext:
        """Create RunContext automatically (model + usage + deps)."""
        ctx = RunContext(
            model=self.model,
            deps=Claim_radar_Deps(resources=resources),
            usage=Usage()
        )
        return ctx

    async def _create_agent(self, system_prompt: str) -> Agent:
        """Internal method to define the agent + tools."""
        agent = Agent(
            model=self.model,
            system_prompt=system_prompt,
            deps_type=Claim_radar_Deps,
            output_type=FinalAgentOutput,
            model_settings=self.m
        )

        # Tool: fetch a site
        @agent.tool
        def fetch_site_tool(ctx: RunContext,url: str) -> SiteDoc:
            """Crawl and return a site's markdown."""
            return fetch_site(url)

        # Tool: search the web
        @agent.tool
        def search_tool(ctx: RunContext, query: str, limit: int = 5) -> SearchResults:
            """Perform web search and return structured results."""
            try:
                raw = search_web(query, limit=limit)
                items = [
                    SearchResultItem(
                        url=r["url"],
                        title=r.get("title"),
                        snippet=r.get("snippet")
                    ) for r in raw
                ]
                return SearchResults(query=query, results=items)
            except Exception as e:
                raise RuntimeError(f"search_tool failed: {e}")

        return agent

    async def claim_verifier(self, resources: List[str], sensitivity: int, input_id: str, md_path: str, raw_texts: List[str] = None):
        """Main entrypoint — handles verification, caching, and context creation internally."""
        from services.neo4j_service import neo4j_service, VerificationResult

        # Step 1: Read input markdown
        markdown_content = self._read_markdown_file(md_path)

        # Step 2: Cache check
        text_hash = neo4j_service.calculate_text_hash(markdown_content)
        cached_result = neo4j_service.get_verification_by_hash(text_hash)
        if cached_result:
            print(f"🎯 Found cached match for {input_id}")
            return cached_result

        # Step 3: Keyword-based similarity cache
        keywords = neo4j_service.extract_keywords(markdown_content)
        similar_results = neo4j_service.find_similar_verifications(keywords, threshold=0.7)
        if similar_results:
            print(f"🎯 Found similar verification for {input_id}")
            return similar_results[0]

        print(f"🔄 No cache found — running agent for {input_id}")

        # Step 4: Create context (automatically handles model + deps)
        ctx = await self._create_context(resources)

        # Step 5: Create agent
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
   - **Step 6**: MANDATORY - Extract the EXACT original passages into misinfo and rightinfo fields

## Data Collection and Analysis:
- **From Search Results**: Extract URLs, titles, and snippets for initial assessment
- **From Crawled Content**: Analyze full markdown content for detailed verification
- **From User-Trusted Sources**: Give higher weight to information from `ctx.deps.resources`
- **Cross-Reference**: Compare findings across multiple sources to establish accuracy

## Output Requirements:
For domain-relevant content, provide a structured response with:

- **Correctness**: bool - True if the information is accurate and verified, False if it contains misinformation or cannot be verified
- **Out_of_domain**: bool - True if content is outside the defined domains, False if within scope
- **misinfo_indices**: List[int] - List of 0-based indices of passages that contain misinformation
- **rightinfo_indices**: List[int] - List of 0-based indices of passages that are factually correct
- **confidence_score**: str - A score from "0.0" to "1.0" indicating your confidence in the verification ("1.0" = very confident, "0.0" = uncertain)
- **sources**: List[str] - List of URLs and source names that support your verification findings

## Critical Instructions for index-based classification:
- **misinfo_indices**: List the 0-based index numbers of passages that contain false information, misleading claims, or unverified rumors
- **rightinfo_indices**: List the 0-based index numbers of passages that are factually accurate and well-sourced
- **Index numbering**: Start from 0 for the first passage, 1 for the second, etc.
- **Example**: If input has 3 passages and passage 0 is correct, passages 1 and 2 are misinformation:
  - rightinfo_indices: [0]
  - misinfo_indices: [1, 2]

## MANDATORY: You MUST classify ALL passages by index
- Do NOT leave misinfo_indices or rightinfo_indices empty
- Every passage must be classified as either correct or misinformation
- Use 0-based indexing (first passage = 0, second = 1, etc.)
- If all passages are correct, put all indices in rightinfo_indices and leave misinfo_indices empty
- If all passages are incorrect, put all indices in misinfo_indices and leave rightinfo_indices empty

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

        agent = await self._create_agent(system_prompt)

        # Step 6: Run agent
        user_input = f"""TASK: Analyze each numbered passage below and classify them by index.

REQUIRED OUTPUT FORMAT:
- rightinfo_indices: List of 0-based indices of factually correct passages
- misinfo_indices: List of 0-based indices of passages containing false information

EXAMPLE:
If passages are:
0. "COVID vaccines work"
1. "Bleach cures COVID"
2. "Climate change is real"

Then output should be:
- rightinfo_indices: [0, 2]
- misinfo_indices: [1]

NUMBERED PASSAGES TO ANALYZE:
{markdown_content}

MANDATORY RULES:
1. Use 0-based indexing (first passage = 0, second = 1, etc.)
2. Classify EVERY passage as either correct or misinformation
3. Do NOT leave index lists empty
4. All passages are within global crises domains (pandemics, geopolitical conflicts, climate events)
5. Use search and fetch tools to verify each claim before categorizing"""

        try:
            response = await agent.run(user_input)
            response_data = response.output

            # Step 7: Store in Neo4j
            # Filter passages based on agent's classification
            if raw_texts is None:
                # Fallback to splitting markdown if raw_texts not provided
                passages = markdown_content.split('\n')
            else:
                passages = raw_texts
                
            misinfo_passages = [passages[i] for i in response_data.misinfo_indices if i < len(passages)]
            rightinfo_passages = [passages[i] for i in response_data.rightinfo_indices if i < len(passages)]
            
            verification_result = VerificationResult(
                input_id=input_id,
                keywords=keywords,
                correctness=response_data.Correctness,
                out_of_domain=response_data.Out_of_domain,
                misinfo=" | ".join(misinfo_passages),
                rightinfo=" | ".join(rightinfo_passages),
                confidence_score=response_data.confidence_score,
                sources=response_data.sources,
                created_at=datetime.now(),
                raw_text_hash=text_hash
            )
            neo4j_service.store_verification(verification_result)

            # Step 8: Save JSON response with filtered passages
            responses_dir = Path(__file__).parent.parent / "responses"
            responses_dir.mkdir(parents=True, exist_ok=True)
            output_path = responses_dir / f"{input_id}_verification.json"
            
            # Create response with filtered passages
            response_with_passages = {
                "Correctness": response_data.Correctness,
                "Out_of_domain": response_data.Out_of_domain,
                "misinfo": " | ".join(misinfo_passages),
                "rightinfo": " | ".join(rightinfo_passages),
                "misinfo_indices": response_data.misinfo_indices,
                "rightinfo_indices": response_data.rightinfo_indices,
                "confidence_score": response_data.confidence_score,
                "sources": response_data.sources
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(response_with_passages, f, indent=2)

            print(f"✅ Saved response to {output_path}")
            return response_data

        except Exception as e:
            raise RuntimeError(f"Agent verification failed: {e}")
