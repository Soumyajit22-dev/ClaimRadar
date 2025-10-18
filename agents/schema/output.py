from typing import Optional, List
from pydantic import BaseModel, Field


class SummarizedContent(BaseModel):
    content:str= Field(..., description="Summarized content of the paased input in markdown format")

class FinalAgentOutput:
    Correctness:bool=Field(...,description="The passed input is right or valid information or not (True or False)")
    Out_of_domain:bool=Field(...,description="The content is out of domain [Global crises like pandemics, geopolitical conflicts and climate events] or not (True or False)")
    misinfo:str = Field(..., description="Misinformation which is present in the passed input"),
    rightinfo:str = Field(..., description="The actual right information which is replced by misinformation in input"),
    confidence_score:str = Field(..., description="How much confidence LLM has on the given result on the information, score should be in range(0 to 1)"),
    sources:List[str] = Field(..., description="The sources from which LLM got the validity that the current information is rightinformation or misinformation")