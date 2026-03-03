from fastapi import APIRouter, HTTPException

from app.models.user_models import AuthenticateRequest, AuthenticateResponse


def build_router(container) -> APIRouter:
    router = APIRouter(prefix="", tags=["identity"])

    @router.post("/authenticate", response_model=AuthenticateResponse)
    async def authenticate(request: AuthenticateRequest):
        user = await container.user_service.authenticate(request)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user

    return router
