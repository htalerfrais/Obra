import logging
from datetime import datetime
from typing import List, Tuple

from app.config import settings
from app.models.tool_models import ToolDefinition
from app.models.chat_models import SearchFilters
from app.models.session_models import ClusterResult, ClusterItem
from app.modules.session_intelligence.application.search_use_case import SearchUseCase
from .base import BaseTool

logger = logging.getLogger(__name__)


class SearchHistoryTool(BaseTool):
    """Semantic search over the user's browsing history clusters and items."""

    _DEFINITION = ToolDefinition(
        name="search_history",
        description=(
            "Search the user's browsing history. Use when the user asks about "
            "pages they visited, topics they explored, or browsing patterns. "
            "You can call this tool multiple times with different queries to "
            "compare topics or gather broader information."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Semantic search query describing what to look for",
                },
                "date_from": {
                    "type": "string",
                    "description": "ISO date (YYYY-MM-DD), only items visited after this date",
                },
                "date_to": {
                    "type": "string",
                    "description": "ISO date (YYYY-MM-DD), only items visited before this date",
                },
                "title_contains": {
                    "type": "string",
                    "description": "Filter: only items with this keyword in the title",
                },
                "domain_contains": {
                    "type": "string",
                    "description": "Filter: only items from domains containing this keyword",
                },
            },
            "required": ["query"],
        },
    )

    def __init__(self, search_use_case: SearchUseCase):
        self.search_use_case = search_use_case

    @property
    def definition(self) -> ToolDefinition:
        return self._DEFINITION

    async def execute(self, user_id: int, arguments: dict) -> Tuple[str, List[dict]]:
        filters = self._parse_filters(arguments)

        logger.info(f"search_history: query='{filters.query_text}', filters={filters}")

        clusters, items = await self.search_use_case.search(
            user_id=user_id,
            filters=filters,
        )

        content = self._format_results(clusters, items)
        logger.info(f"search_history returned {len(clusters)} clusters, {len(items)} items")

        sources = [
            {
                "url": item.url,
                "title": item.title,
                "visit_time": item.visit_time,
                "url_hostname": item.url_hostname,
            }
            for item in items
        ]

        return content, sources

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_filters(arguments: dict) -> SearchFilters:
        date_from = None
        date_to = None
        if arguments.get("date_from"):
            try:
                date_from = datetime.fromisoformat(arguments["date_from"])
            except ValueError:
                logger.warning(f"Invalid date_from: {arguments['date_from']}")
        if arguments.get("date_to"):
            try:
                date_to = datetime.fromisoformat(arguments["date_to"])
                # If only a date was provided (no time), extend to end of day
                if date_to.hour == 0 and date_to.minute == 0 and date_to.second == 0:
                    date_to = date_to.replace(hour=23, minute=59, second=59)
            except ValueError:
                logger.warning(f"Invalid date_to: {arguments['date_to']}")

        return SearchFilters(
            query_text=arguments.get("query"),
            date_from=date_from,
            date_to=date_to,
            title_contains=arguments.get("title_contains"),
            domain_contains=arguments.get("domain_contains"),
        )

    @staticmethod
    def _format_results(clusters: List[ClusterResult], items: List[ClusterItem]) -> str:
        if not clusters and not items:
            return "No relevant browsing history found."

        parts: List[str] = []

        if clusters:
            parts.append("Relevant browsing themes:")
            for c in clusters:
                parts.append(f"• {c.theme}: {c.summary}")

        if items:
            parts.append("\nRelevant pages visited:")
            for item in items:
                title = item.title or "Untitled"
                domain = item.url_hostname or ""
                url = item.url or ""
                visit_date = item.visit_time.strftime('%Y-%m-%d %H:%M') if item.visit_time else ""
                parts.append(f"• {title} ({domain}) - visited: {visit_date} - {url}")

        return "\n".join(parts)
