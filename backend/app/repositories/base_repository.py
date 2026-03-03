from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, Optional
import logging

from app.database import SessionLocal

logger = logging.getLogger(__name__)


class BaseRepository:
    @contextmanager
    def _get_session(self):
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _execute(self, operation: Callable, error_msg: str = "Operation failed") -> Optional[Any]:
        try:
            with self._get_session() as db:
                return operation(db)
        except Exception as exc:
            logger.error("%s: %s", error_msg, str(exc))
            return None

    @staticmethod
    def _to_dict(obj) -> Dict:
        if obj is None:
            return {}
        result = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
