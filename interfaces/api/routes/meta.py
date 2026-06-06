from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@router.get("/health", tags=["Meta"], status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy"}
