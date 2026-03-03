import logging
from datetime import datetime
from typing import List, Tuple

from app.models.tool_models import ToolDefinition
from app.modules.session_intelligence.application.browsing_query_use_case import BrowsingQueryUseCase
from .base import BaseTool

logger = logging.getLogger(__name__)


class ListSessionsTool(BaseTool):
    """List a user's browsing sessions with dates and cluster themes."""

    _DEFINITION = ToolDefinition(
        name="list_sessions",
        description=(
            "List the user's browsing sessions with their dates, durations and "
            "thematic clusters. Use when the user asks about their sessions, "
            "what they did on a specific day, or wants an overview of recent activity."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of sessions to return (default 10)",
                },
                "date_from": {
                    "type": "string",
                    "description": "ISO date (YYYY-MM-DD), only sessions after this date",
                },
                "date_to": {
                    "type": "string",
                    "description": "ISO date (YYYY-MM-DD), only sessions before this date",
                },
            },
            "required": [],
        },
    )

    def __init__(self, browsing_query_use_case: BrowsingQueryUseCase):
        self.browsing_query_use_case = browsing_query_use_case

    @property
    def definition(self) -> ToolDefinition:
        return self._DEFINITION

    async def execute(self, user_id: int, arguments: dict) -> Tuple[str, List[dict]]:
        limit = arguments.get("limit", 10)
        date_from = self._parse_date(arguments.get("date_from"))
        date_to = self._parse_date(arguments.get("date_to"))

        # If only a date was provided (no time), extend to end of day
        if date_to and date_to.hour == 0 and date_to.minute == 0 and date_to.second == 0:
            date_to = date_to.replace(hour=23, minute=59, second=59)

        sessions = self.browsing_query_use_case.list_sessions(
            user_id=user_id,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )

        if not sessions:
            return "No browsing sessions found for the given criteria.", []

        lines = [f"Found {len(sessions)} session(s):"]
        for s in sessions:
            start = self._format_datetime(s.get("start_time"))
            end = self._format_datetime(s.get("end_time"))
            themes = ", ".join(s.get("cluster_names", [])) or "no themes"
            lines.append(f"• {start} → {end} | Themes: {themes}")

        return "\n".join(lines), []

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            logger.warning(f"Invalid date value: {value}")
            return None

    @staticmethod
    def _format_datetime(value) -> str:
        if value is None:
            return "?"
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime("%Y-%m-%d %H:%M")
