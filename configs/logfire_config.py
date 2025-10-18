import logging
from fastapi import FastAPI

def init_logging(app: FastAPI):
    """Initialize logging for the FastAPI application"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("app.log")
        ]
    )
    
    # Set up logger for the app
    logger = logging.getLogger(app.title)
    logger.setLevel(logging.INFO)

def setup_logger(name: str) -> logging.Logger:
    """Setup logger for a specific module"""
    return logging.getLogger(name)
