import httpx
import logging
import time
from typing import Optional

from app.config import settings
from app.models.user_models import TokenInfo
from app.monitoring import get_request_id

logger = logging.getLogger(__name__)
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class GoogleAuthAdapter:
    async def validate_token(self, token: str) -> Optional[TokenInfo]:
        start = time.perf_counter()
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=settings.api_timeout) as client:
                response = await client.get(
                    GOOGLE_TOKENINFO_URL,
                    params={"access_token": token},
                )
            duration_ms = (time.perf_counter() - start) * 1000
            if response.status_code != 200:
                logger.info(
                    "auth_validation",
                    extra={
                        "request_id": get_request_id(),
                        "validation_success": False,
                        "duration_ms": round(duration_ms, 2),
                        "status_code": response.status_code,
                    },
                )
                return None
            data = response.json()
            sub = data.get("sub")
            if not sub:
                return None
            return TokenInfo(
                google_user_id=sub,
                email=data.get("email"),
                expires_in=int(data.get("expires_in", 0)),
            )
        except Exception as exc:
            logger.error(
                "auth_validation",
                extra={
                    "request_id": get_request_id(),
                    "validation_success": False,
                    "error": str(exc),
                },
            )
            return None
