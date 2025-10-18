import uuid
import os
import json
from pathlib import Path
from fastapi import UploadFile
from db.models import Document
from configs.config import get_settings
from db.database import get_db_context

settings = get_settings()

async def validate_pdf_file(file: UploadFile) -> bool:
    """
    Validate that the uploaded file is a PDF
    """
    if not file or not file.filename:
        return False
        
    content_type = file.content_type
    filename = file.filename
    
    # Check content type
    if content_type != "application/pdf":
        return False
    
    # Check file extension
    if not filename.lower().endswith('.pdf'):
        return False
    
    return True

async def save_file_to_data_folder(file: UploadFile, data_folder: str = "data") -> str:
    """
    Save the uploaded PDF file to the data folder with its original filename
    Returns the file path where the file was saved
    """
    if not file or not file.filename:
        raise ValueError("Invalid file provided")
        
    # Ensure data folder exists
    data_path = Path(data_folder)
    data_path.mkdir(exist_ok=True)
    
    # Create file path with original filename
    file_path = data_path / file.filename
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Write file to disk
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Reset file pointer for potential future use
        await file.seek(0)
        
        return str(file_path)
    except Exception as e:
        raise ValueError(f"Failed to save file: {str(e)}")


async def save_processed_file(response_path: str, user_id: str, pdf_path:str) -> Document:
    """
    Read the JSON response file and save the FRA data to the database
    """
    with get_db_context() as db:
        try:
            # Ensure we have the full path
            if not os.path.isabs(response_path):
                # If it's a relative path, make it absolute from the project root
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                response_path = os.path.join(project_root, response_path)
            
            # Check if file exists
            if not os.path.exists(response_path):
                raise FileNotFoundError(f"Response file not found: {response_path}")
            
            # Read the JSON response file
            with open(response_path, 'r', encoding='utf-8') as f:
                fra_data = json.load(f)
            
            # Check if user exists, if not create a default user or set owner to None
            from db.models import User
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                # If the provided user does not exist, avoid FK violation by setting owner to None
                print("User not exists..")
                user_id = None
            
            # Create document record with FRA data
            document = Document(
                id=str(uuid.uuid4()),
                owner=user_id,
                filename=os.path.basename(pdf_path),
                content_type='application/pdf',
                file_size=0,  # Will be updated when actual file is processed
                file_content=b'',  # Empty for now, will be filled when processing
                status='COMPLETED',
                
                # FRA data fields
                patta_number=fra_data.get('patta_number'),
                claim_type=fra_data.get('claim_type'),
                claimant_names=fra_data.get('claimant_names'),
                tribe_or_group=fra_data.get('tribe_or_group'),
                village=fra_data.get('village'),
                block=fra_data.get('block'),
                district=fra_data.get('district'),
                survey_number=fra_data.get('survey_number'),
                area_granted_ha=fra_data.get('area_granted_ha'),
                coordinates=fra_data.get('coordinates'),
                issue_date=fra_data.get('issue_date'),
                status_remarks=fra_data.get('remarks'),
                state=fra_data.get('state'),
                country=fra_data.get('country'),
                is_active=False,
                is_verified=fra_data.get('is_verified'),
                is_approved=False
            )

            # Save to database
            db.add(document)
            db.commit()
            db.refresh(document)
            return document
            
        except FileNotFoundError:
            raise ValueError(f"Response file not found: {response_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response file: {e}")
        except Exception as e:
            raise ValueError(f"Error processing response file: {e}")

def get_document_file(document: Document) -> bytes:
    """
    Retrieve the file content from the database
    """
    return document.file_content

def delete_document_file(document: Document) -> bool:
    """
    Delete document from the database
    """
    with get_db_context() as db:
        try:
            db.delete(document)
            db.commit()
            return True
        except Exception:
            return False 