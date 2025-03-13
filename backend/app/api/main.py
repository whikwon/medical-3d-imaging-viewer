from fastapi import APIRouter

from app.api.routes import orthanc

api_router = APIRouter()
api_router.include_router(orthanc.router, prefix="/orthanc", tags=["orthanc"])
