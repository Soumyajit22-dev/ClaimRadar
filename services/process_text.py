import asyncio
from pathlib import Path
from typing import List
from bs4 import BeautifulSoup
import tiktoken


async def process_raw_text(input_id: str, texts: list) -> list:
    # text -> beautifulsoup -> parsed text list
    # input_id is passed to track the list by callers; not used here
    if not isinstance(texts, list):
        raise ValueError("texts must be a list of strings")
    result = []
    if input_id:
        for item in texts:
            text_item = "" if item is None else str(item)
            soup = BeautifulSoup(text_item, 'html.parser')
            parsed_text = soup.get_text().strip()
            result.append([parsed_text])

    return result


def _count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def _batch_texts_by_tokens(texts: List[str], max_tokens: int, separator: str) -> List[List[str]]:
    batches: List[List[str]] = []
    current_batch: List[str] = []
    current_tokens = 0
    sep_tokens = _count_tokens(separator)

    for text in texts:
        candidate_tokens = _count_tokens(text)
        extra = sep_tokens if current_batch else 0
        if current_batch and current_tokens + extra + candidate_tokens > max_tokens:
            batches.append(current_batch)
            current_batch = [text]
            current_tokens = candidate_tokens
        else:
            if current_batch:
                current_tokens += sep_tokens
            current_batch.append(text)
            current_tokens += candidate_tokens
    if current_batch:
        batches.append(current_batch)
    return batches

