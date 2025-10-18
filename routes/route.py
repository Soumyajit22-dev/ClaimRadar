from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, status, Request
from pydantic import Field
from datetime import datetime
from typing import List
import os
from schemas import DocumentStatus, AgentResponse
from configs.config import get_settings
from agents.agent import Process_agent
from agents.core_agent import Claimradar_agent
from services.process_text import process_raw_text
router = APIRouter()

settings = get_settings()

@router.post("/process_text", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def process(
    request: Request,
    raw_texts: List[str] = [],
    input_id: str = '',
    resources: List[str] = [],
    sensitivity: int = 0,
    background_tasks: BackgroundTasks = None
):
    #text -> beautifulsoup -> .md -> LLM -> summary of the text ->system promptm + user recommended sources + Fixed recommended sources

    try:
        processed_raw_texts = await process_raw_text(input_id, raw_texts)
        process_agent = Process_agent()
        summarized_md_path = await process_agent.summarize_texts_to_markdown(input_id=input_id, raw_texts=processed_raw_texts)
        try:
            Claimradar_agent = Claimradar_agent()
            response_data = await Claimradar_agent.claim_verifier(input_id=input_id, resources=resources, sensitivity=sensitivity, md_path=summarized_md_path)
            
        except Exception as e:
            raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process raw text: {str(e)}"
        )
        response = AgentResponse(
            id=input_id,
            success=True
        )
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process raw text: {str(e)}"
        )
    
   
