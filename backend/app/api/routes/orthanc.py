from fastapi import APIRouter, Request, Response
import httpx
from starlette.background import BackgroundTask

from app.core.config import settings

router = APIRouter()

# Create a single client for reuse
client = httpx.AsyncClient(base_url=settings.ORTHANC_URL)


# Close client when application shuts down
@router.api_route(
    "/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def proxy(full_path: str, request: Request):
    # Construct the Orthanc URL based on the incoming request path
    url = f"/{full_path}"

    # Forward the request with its method, headers, and body.
    response = await client.request(
        method=request.method,
        url=url,
        headers=request.headers,
        params=request.query_params,
        content=await request.body(),
    )

    # For binary responses (like DICOM files), stream the response directly
    # instead of buffering in memory
    is_binary = "application/dicom" in response.headers.get("Content-Type", "")

    headers = dict(response.headers)

    # Add cache control headers for DICOM files to improve performance
    if is_binary or "/file" in full_path:
        headers["Cache-Control"] = "public, max-age=86400"  # Cache for 24 hours

    # Return the response from Orthanc back to the client
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=headers,
        background=BackgroundTask(response.aclose),
    )
