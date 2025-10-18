from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
import os, secrets, uvicorn
from configs.logfire_config import init_logging, setup_logger
from routes import route
from configs.config import get_settings
from routes.route import router as ocr_router

settings = get_settings()

# Create upload directory if it doesn't exist
os.makedirs(settings.app_config.upload_dir, exist_ok=True)
security = HTTPBasic()

app = FastAPI(
    title=settings.app_config.project_name
)

init_logging(app)
logger = setup_logger(__name__)

root_router = APIRouter()


def custom_openapi():
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add the JWT security scheme to the OpenAPI schema
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }

    # Apply the JWT security scheme to all API routes
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"bearerAuth": []}]
    return openapi_schema


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.app_config.allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", status_code=200)
def hello_world():
    return "Server is running!"

@app.get("/health")
def health_check():
    return {"status": "UP"}

@app.get("/version")
def get_version():
    return "v1"


# Include routers
root_router.include_router(route.router, prefix=f"{settings.app_config.api_v1_str}/files", tags=["files"])
app.include_router(root_router)
app.include_router(ocr_router)

if __name__ == "__main__":
    uvicorn.run("main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )