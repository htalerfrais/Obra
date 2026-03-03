from dataclasses import dataclass
from typing import Callable, Dict

from app.modules.assistant.application.chat_use_case import ChatUseCase
from app.modules.assistant.application.tool_gateway import ToolGateway
from app.modules.assistant.infrastructure.langgraph_runtime import LangGraphChatRuntime
from app.modules.identity.application.user_use_case import UserUseCase
from app.modules.identity.infrastructure.google_auth_adapter import GoogleAuthAdapter
from app.modules.learning_content.application.learning_content_service import LearningContentService
from app.modules.outbox.application.outbox_service import OutboxPublisher
from app.modules.recall_engine.application.recall_service import RecallService
from app.modules.session_intelligence.application.browsing_query_use_case import BrowsingQueryUseCase
from app.modules.session_intelligence.application.search_use_case import SearchUseCase
from app.modules.session_intelligence.application.session_intelligence_use_case import SessionIntelligenceUseCase
from app.modules.session_intelligence.infrastructure.clustering_engine import ClusteringEngine
from app.modules.session_intelligence.infrastructure.persistence_mapper import SessionPersistenceMapper
from app.modules.shared.infrastructure.embedding_client import EmbeddingClient
from app.modules.shared.infrastructure.llm_client import LLMClient
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.learning_repository import LearningRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.search_repository import SearchRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.topic_repository import TopicRepository
from app.repositories.user_repository import UserRepository
from app.tools.registry import ToolRegistry
from app.tools.search_tool import SearchHistoryTool
from app.tools.session_tools import ListSessionsTool
from app.tools.stats_tools import BrowsingStatsTool


@dataclass
class AppContainer:
    # Data access
    user_repository: UserRepository
    session_repository: SessionRepository
    search_repository: SearchRepository
    topic_repository: TopicRepository
    learning_repository: LearningRepository
    outbox_repository: OutboxRepository
    analytics_repository: AnalyticsRepository

    # Shared adapters
    embedding_client: EmbeddingClient
    llm_client: LLMClient
    google_auth_adapter: GoogleAuthAdapter

    # Use-cases
    user_service: UserUseCase
    browsing_query_use_case: BrowsingQueryUseCase
    search_use_case: SearchUseCase
    clustering_engine: ClusteringEngine
    persistence_mapper: SessionPersistenceMapper
    tool_registry: ToolRegistry
    tool_gateway: ToolGateway

    outbox_publisher: OutboxPublisher
    outbox_handlers: Dict[str, Callable[[dict], None]]
    session_intelligence_use_case: SessionIntelligenceUseCase
    recall_service: RecallService
    learning_content_service: LearningContentService
    langgraph_chat_runtime: LangGraphChatRuntime
    chat_use_case: ChatUseCase


def build_container() -> AppContainer:
    user_repository = UserRepository()
    session_repository = SessionRepository()
    search_repository = SearchRepository()
    topic_repository = TopicRepository()
    learning_repository = LearningRepository()
    outbox_repository = OutboxRepository()
    analytics_repository = AnalyticsRepository()

    embedding_client = EmbeddingClient()
    llm_client = LLMClient()
    google_auth_adapter = GoogleAuthAdapter()
    user_service = UserUseCase(user_repository=user_repository, google_auth_adapter=google_auth_adapter)

    persistence_mapper = SessionPersistenceMapper(session_repository=session_repository)
    clustering_engine = ClusteringEngine(
        llm_client=llm_client,
        embedding_client=embedding_client,
        persistence_mapper=persistence_mapper,
    )
    browsing_query_use_case = BrowsingQueryUseCase(session_repository, analytics_repository)
    search_use_case = SearchUseCase(search_repository=search_repository, embedding_client=embedding_client)

    search_tool = SearchHistoryTool(search_use_case)
    session_tool = ListSessionsTool(browsing_query_use_case)
    stats_tool = BrowsingStatsTool(browsing_query_use_case)
    tool_registry = ToolRegistry([search_tool, session_tool, stats_tool])
    tool_gateway = ToolGateway(tool_registry)

    outbox_publisher = OutboxPublisher(outbox_repository)
    session_intelligence_use_case = SessionIntelligenceUseCase(clustering_engine, outbox_publisher)
    recall_service = RecallService(topic_repository, session_repository)
    learning_content_service = LearningContentService(llm_client, learning_repository, topic_repository)
    langgraph_chat_runtime = LangGraphChatRuntime(llm_client, tool_gateway)
    chat_use_case = ChatUseCase(langgraph_chat_runtime, user_service)
    outbox_handlers = {
        "SessionClustered.v1": lambda payload: recall_service.recompute(user_id=int(payload.get("user_id")), topic_id=None),
        "TopicRecallDue.v1": lambda payload: None,
        "QuizRequested.v1": lambda payload: None,
    }

    return AppContainer(
        user_repository=user_repository,
        session_repository=session_repository,
        search_repository=search_repository,
        topic_repository=topic_repository,
        learning_repository=learning_repository,
        outbox_repository=outbox_repository,
        analytics_repository=analytics_repository,
        embedding_client=embedding_client,
        llm_client=llm_client,
        google_auth_adapter=google_auth_adapter,
        user_service=user_service,
        browsing_query_use_case=browsing_query_use_case,
        search_use_case=search_use_case,
        clustering_engine=clustering_engine,
        persistence_mapper=persistence_mapper,
        tool_registry=tool_registry,
        tool_gateway=tool_gateway,
        outbox_publisher=outbox_publisher,
        outbox_handlers=outbox_handlers,
        session_intelligence_use_case=session_intelligence_use_case,
        recall_service=recall_service,
        learning_content_service=learning_content_service,
        langgraph_chat_runtime=langgraph_chat_runtime,
        chat_use_case=chat_use_case,
    )
