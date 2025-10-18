import os
import json
import sys
import asyncio
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from services.process_text import _count_tokens
from services.process_text import _batch_texts_by_tokens
from models.base import get_model

# Add the parent directory to the Python path to allow imports from agent_output
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from agents.schema.output import SummarizedContent


model, model_settings = get_model()

class Process_agent:
    def __init__(self, model = model):
        self.model = model


    def _read_markdown_file(self, file_path: str) -> str:
        """Read and return content of markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
        

    async def Summarize_agent(self, system_prompt: str)-> Agent:
        agent = Agent(
            model=self.model,
            system_prompt= system_prompt,
            output_type=SummarizedContent ,
            model_settings = model_settings
        )
        return agent
            
    async def summarize_texts_to_markdown(self, input_id: str, raw_texts: List[str], max_tokens_per_batch: int = 6000) -> str:
        # Clean inputs via BeautifulSoup
        
        separator = "\n Next_line:"
        # Flatten any nested lists into strings if needed
        flattened_texts: List[str] = []
        for item in raw_texts:
            if isinstance(item, list):
                flattened_texts.append(" ".join(str(x) for x in item))
            else:
                flattened_texts.append(str(item))

        batches = _batch_texts_by_tokens(flattened_texts, max_tokens_per_batch, separator)

        system_prompt = (
            "You are a precise summarizer. Summarize the provided lines into a cohesive,"
            " accurate markdown document while preserving key details, numbers, and entity names."
        )

        agent = await self.Summarize_agent(system_prompt=system_prompt)

        async def run_batch(batch: List[str]) -> str:
            user_input = separator.join(batch)
            response = await agent.run(user_input)
            return response.output.content if hasattr(response.output, 'content') else str(response.output)

        # Run all batches concurrently; gather preserves order
        batch_markdowns = await asyncio.gather(*[run_batch(batch) for batch in batches])

        final_markdown = "\n\n".join(batch_markdowns)

        # Write final markdown to file
        project_root = Path(__file__).resolve().parents[1]
        summaries_dir = project_root / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)
        output_path = summaries_dir / f"{input_id}.md"
        output_path.write_text(final_markdown, encoding='utf-8')
        return str(output_path)


# if __name__ == "__main__":
#     import asyncio
#     process_agent = Process_agent()
#     # Example of running a single document
#     response = asyncio.run(process_agent.process_doc(markdown_file="/Users/soumyajitmondal/Documents/FRA/pdf_output/page_14.md"))
#     print(f"Processing completed successfully: {response}")