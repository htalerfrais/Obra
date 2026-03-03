import json
from typing import Dict, List, Optional

import numpy as np

from app.config import settings
from app.models.llm_models import LLMRequest
from app.models.session_models import ClusterItem, ClusterResult, HistorySession, SemanticGroup, SessionClusteringResponse
from app.modules.shared.infrastructure.embedding_client import EmbeddingClient
from app.modules.shared.infrastructure.llm_client import LLMClient
from app.modules.session_intelligence.infrastructure.persistence_mapper import SessionPersistenceMapper

GENERIC_CLUSTER = {"cluster_id": "cluster_generic", "theme": "General Browsing", "summary": "Miscellaneous browsing activity."}


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class ClusteringEngine:
    def __init__(
        self,
        llm_client: LLMClient,
        embedding_client: EmbeddingClient,
        persistence_mapper: Optional[SessionPersistenceMapper] = None,
    ):
        self.llm_client = llm_client
        self.embedding_client = embedding_client
        self.persistence_mapper = persistence_mapper

    async def cluster_session(self, session: HistorySession, user_id: int, force: bool = False) -> SessionClusteringResponse:
        canonical_identifier = f"u{user_id}:{session.session_identifier}"
        if self.persistence_mapper and not force:
            cached = self.persistence_mapper.load(canonical_identifier)
            if cached:
                return cached

        groups = self._create_groups(session)
        groups = await self._embed_groups(groups)
        cluster_meta = await self._identify_clusters(groups)
        cluster_meta = await self._embed_clusters(cluster_meta)
        cluster_to_groups = self._assign_groups(groups, cluster_meta)
        cluster_to_items = self._decompress(cluster_to_groups)

        cluster_results: List[ClusterResult] = []
        for meta in cluster_meta:
            cid = meta.get("cluster_id")
            items = cluster_to_items.get(cid, [])
            if not items:
                continue
            cluster_results.append(
                ClusterResult(
                    cluster_id=cid,
                    theme=meta.get("theme", "Miscellaneous"),
                    summary=meta.get("summary", ""),
                    items=items,
                    embedding=meta.get("embedding"),
                    is_learning=meta.get("is_learning", False),
                )
            )
        generic_items = cluster_to_items.get(GENERIC_CLUSTER["cluster_id"], [])
        if generic_items:
            cluster_results.append(
                ClusterResult(
                    cluster_id=GENERIC_CLUSTER["cluster_id"],
                    theme=GENERIC_CLUSTER["theme"],
                    summary=GENERIC_CLUSTER["summary"],
                    items=generic_items,
                    embedding=None,
                )
            )

        response = SessionClusteringResponse(
            session_identifier=canonical_identifier,
            session_start_time=session.start_time,
            session_end_time=session.end_time,
            clusters=cluster_results,
        )
        if self.persistence_mapper:
            self.persistence_mapper.save(user_id=user_id, response=response, replace_if_exists=force)
        return response

    def _create_groups(self, session: HistorySession) -> List[SemanticGroup]:
        groups: Dict[str, List] = {}
        no_title_counter = 0
        for item in session.items:
            title = item.title.strip() if item.title else ""
            hostname = item.url_hostname or ""
            if not title:
                key = f"__notitle__{no_title_counter}::{hostname}"
                no_title_counter += 1
            else:
                key = f"{title}::{hostname}"
            groups.setdefault(key, []).append(item)
        result = []
        for key, items in groups.items():
            first = items[0]
            result.append(
                SemanticGroup(
                    group_key=key,
                    title=first.title.strip() if first.title else "",
                    hostname=first.url_hostname or "",
                    item_count=len(items),
                    example_visit_time=first.visit_time,
                    example_pathname_clean=first.url_pathname_clean,
                    items=items,
                    embedding=None,
                )
            )
        return result

    async def _embed_groups(self, groups: List[SemanticGroup]) -> List[SemanticGroup]:
        texts: List[str] = []
        indices: List[int] = []
        for idx, group in enumerate(groups):
            text = group.title or group.hostname
            if text:
                texts.append(text[:1200])
                indices.append(idx)
        if not texts:
            return groups
        vectors = await self.embedding_client.embed_texts(texts)
        for idx, vector in zip(indices, vectors):
            groups[idx].embedding = vector if vector else None
        return groups

    async def _identify_clusters(self, groups: List[SemanticGroup]) -> List[Dict]:
        simplified = [{"title": g.title, "hostname": g.hostname} for g in groups]
        prompt = f"""
            You are classifying browsing clusters for learning detection.

            Task:
            Return a JSON array of thematic clusters.
            Each item must contain:
            - cluster_id (string)
            - theme (string)
            - summary (string)
            - is_learning (boolean)

            Definition of is_learning (STRICT):
            Set is_learning=true ONLY when there is strong evidence of sustained documentation/research/study activity on a specific topic.

            Strong evidence requires MOST of the following:
            1) Depth: multiple meaningful pages in the same topic (not a single page hit).
            2) Continuity: repeated or sustained exploration behavior (not a quick bounce).
            3) Intent: clear learning/research intent (tutorials, docs, API references, troubleshooting, technical Q&A, educational resources).
            4) Focus: coherent topic focus rather than mixed casual browsing.

            Set is_learning=false for:
            - one-off page visits
            - short casual checks
            - social media, entertainment, shopping, generic news scanning
            - productivity navigation without study intent
            - mixed/noisy clusters without clear learning focus

            Conservative policy:
            If uncertain, set is_learning=false.
            Avoid false positives.

            Output rules:
            - Return JSON only (no markdown, no explanation).
            - Boolean must be real JSON booleans: true/false (not strings).
            - Do not invent extra keys.
            - Keep summary concise and factual.

            Browsing groups:
            {json.dumps(simplified, ensure_ascii=False)}
            """
        try:
            response = await self.llm_client.generate_text(
                LLMRequest(
                    prompt=prompt,
                    provider=settings.default_provider,
                    max_tokens=settings.clustering_max_tokens,
                    temperature=settings.clustering_temperature,
                )
            )
            raw = response.generated_text.strip()
            data = self._extract_json(raw)
            if isinstance(data, list):
                cleaned = []
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    cid = str(item.get("cluster_id") or f"cluster_{idx+1}")
                    if cid == "cluster_generic":
                        continue
                    cleaned.append({
                        "cluster_id": cid,
                        "theme": str(item.get("theme") or "Miscellaneous"),
                        "summary": str(item.get("summary") or ""),
                        "is_learning": bool(item.get("is_learning", False)),
                    })
                return cleaned
        except Exception:
            pass
        return []

    async def _embed_clusters(self, clusters_meta: List[Dict]) -> List[Dict]:
        if not clusters_meta:
            return clusters_meta
        texts = [f"{c.get('theme', '')} - {c.get('summary', '')}".strip()[:1200] for c in clusters_meta]
        vectors = await self.embedding_client.embed_texts(texts)
        for cluster, vector in zip(clusters_meta, vectors):
            cluster["embedding"] = vector if vector else []
        return clusters_meta

    def _assign_groups(self, groups: List[SemanticGroup], clusters_meta: List[Dict]) -> Dict[str, List[SemanticGroup]]:
        threshold = settings.clustering_similarity_threshold
        cluster_map: Dict[str, List[SemanticGroup]] = {c["cluster_id"]: [] for c in clusters_meta}
        cluster_map[GENERIC_CLUSTER["cluster_id"]] = []
        valid_clusters = [c for c in clusters_meta if c.get("embedding")]

        for group in groups:
            if not group.embedding:
                cluster_map[GENERIC_CLUSTER["cluster_id"]].append(group)
                continue
            best_cluster = GENERIC_CLUSTER["cluster_id"]
            best_similarity = -1.0
            for cluster in valid_clusters:
                sim = cosine_similarity(group.embedding, cluster["embedding"])
                if sim > best_similarity:
                    best_similarity = sim
                    best_cluster = cluster["cluster_id"]
            if best_similarity >= threshold:
                cluster_map[best_cluster].append(group)
            else:
                cluster_map[GENERIC_CLUSTER["cluster_id"]].append(group)
        return cluster_map

    def _decompress(self, cluster_to_groups: Dict[str, List[SemanticGroup]]) -> Dict[str, List[ClusterItem]]:
        output: Dict[str, List[ClusterItem]] = {}
        for cluster_id, groups in cluster_to_groups.items():
            items: List[ClusterItem] = []
            for group in groups:
                for history_item in group.items:
                    items.append(
                        ClusterItem(
                            url=history_item.url,
                            title=history_item.title,
                            visit_time=history_item.visit_time,
                            url_hostname=history_item.url_hostname,
                            url_pathname_clean=history_item.url_pathname_clean,
                            url_search_query=history_item.url_search_query,
                            embedding=group.embedding,
                        )
                    )
            output[cluster_id] = items
        return output

    @staticmethod
    def _extract_json(text: str):
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        start_idx = min([i for i in [text.find("["), text.find("{")] if i != -1] or [-1])
        if start_idx == -1:
            raise ValueError("No JSON start found")
        end_idx = max(text.rfind("]"), text.rfind("}"))
        if end_idx == -1 or end_idx <= start_idx:
            raise ValueError("No JSON end found")
        return json.loads(text[start_idx:end_idx + 1])
