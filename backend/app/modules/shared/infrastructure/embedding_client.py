from typing import List, Optional
import logging
import time

import httpx

from app.config import settings
from app.monitoring import get_request_id, metrics, calculate_embedding_cost

logger = logging.getLogger(__name__)
BATCH_SIZE = 100


class EmbeddingClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.google_api_key
        self.base_url = (base_url or settings.google_base_url).rstrip("/")
        self.model = model or settings.embedding_model
        self.timeout = settings.api_timeout
        self.embedding_dim = settings.embedding_dim

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self.api_key:
            logger.warning("EmbeddingClient: missing API key, returning empty vectors.")
            return [[] for _ in texts]

        vectors: List[List[float]] = []
        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[batch_start:batch_start + BATCH_SIZE]
            vectors.extend(await self._embed_batch(batch_texts))
        while len(vectors) < len(texts):
            vectors.append([])
        return vectors[:len(texts)]

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        start = time.perf_counter()
        url = f"{self.base_url}/models/{self.model}:batchEmbedContents"
        params = {"key": self.api_key}
        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": self.embedding_dim,
                }
                for text in texts
            ]
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, params=params, json=payload)
            duration_ms = (time.perf_counter() - start) * 1000
            if response.status_code != 200:
                return [[] for _ in texts]
            data = response.json()
            vectors: List[List[float]] = []
            failures = 0
            for emb in data.get("embeddings", []):
                values = emb.get("values", [])
                if isinstance(values, list) and values:
                    vectors.append([float(x) for x in values])
                else:
                    failures += 1
                    vectors.append([])
            metrics.record_embedding(batch_size=len(texts), failures=failures, duration_ms=duration_ms)
            calculate_embedding_cost(settings.embedding_provider, self.model, len(texts))
            return vectors
        except Exception:
            return [[] for _ in texts]
