from typing import Dict, Optional
import logging

from app.models.user_models import AuthenticateRequest
from app.repositories.user_repository import UserRepository
from app.modules.identity.infrastructure.google_auth_adapter import GoogleAuthAdapter

logger = logging.getLogger(__name__)


class UserUseCase:
    def __init__(self, user_repository: UserRepository, google_auth_adapter: GoogleAuthAdapter):
        self.user_repository = user_repository
        self.google_auth_adapter = google_auth_adapter

    async def authenticate(self, request: AuthenticateRequest) -> Optional[Dict]:
        token_info = await self.google_auth_adapter.validate_token(request.token)
        if not token_info:
            logger.warning("Token validation failed")
            return None
        return self.user_repository.get_or_create_by_google_user_id(
            token_info.google_user_id,
            token=request.token,
        )

    async def get_user_from_token(self, token: str) -> Optional[Dict]:
        token_info = await self.google_auth_adapter.validate_token(token)
        if not token_info:
            return None
        return self.user_repository.get_or_create_by_google_user_id(
            token_info.google_user_id,
            token=token,
        )
