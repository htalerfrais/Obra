from typing import Dict, Optional

from app.models.database_models import User
from .base_repository import BaseRepository


class UserRepository(BaseRepository):
    def get_by_google_user_id(self, google_user_id: str) -> Optional[Dict]:
        def operation(db):
            user = db.query(User).filter(User.google_user_id == google_user_id).first()
            return self._to_dict(user) if user else None
        return self._execute(operation, "Failed to get user by google_user_id")

    def get_or_create_by_google_user_id(self, google_user_id: str, token: Optional[str] = None) -> Optional[Dict]:
        def operation(db):
            user = db.query(User).filter(User.google_user_id == google_user_id).first()
            if user:
                if token and user.token != token:
                    user.token = token
                    db.add(user)
                    db.flush()
                    db.refresh(user)
                return self._to_dict(user)
            user = User(google_user_id=google_user_id, token=token)
            db.add(user)
            db.flush()
            db.refresh(user)
            return self._to_dict(user)
        return self._execute(operation, "Failed to get or create user")
