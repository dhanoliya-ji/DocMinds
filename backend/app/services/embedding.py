import hashlib
import random
from typing import List
from app.core.config import settings

class EmbeddingService:
    @classmethod
    def get_embeddings(cls, texts: List[str]) -> List[List[float]]:
        """
        Batch retrieves embeddings for a list of text inputs.
        Dispatches request to the configured EMBEDDING_PROVIDER.
        """
        if not texts:
            return []
            
        provider = settings.EMBEDDING_PROVIDER.lower()
        
        if provider == "openai":
            return cls._get_openai_embeddings(texts)
        elif provider == "huggingface":
            return cls._get_huggingface_embeddings(texts)
        elif provider == "mock":
            return cls._get_mock_embeddings(texts)
        else:
            print(f"[Embedding] Warning: Unknown provider '{provider}'. Falling back to mock embeddings.")
            return cls._get_mock_embeddings(texts)

    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        """
        Helper method to retrieve embedding for a single text input.
        """
        results = cls.get_embeddings([text])
        return results[0] if results else []

    @classmethod
    def _get_openai_embeddings(cls, texts: List[str]) -> List[List[float]]:
        try:
            if not settings.OPENAI_API_KEY:
                print("[Embedding] Warning: OPENAI_API_KEY is missing. Falling back to mock embeddings.")
                return cls._get_mock_embeddings(texts)
                
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = client.embeddings.create(
                input=texts,
                model=settings.OPENAI_EMBEDDING_MODEL
            )
            # OpenAI returns list of embeddings ordered by index
            return [data.embedding for data in response.data]
            
        except Exception as e:
            print(f"[Embedding] OpenAI API call failed: {e}. Falling back to mock embeddings.")
            return cls._get_mock_embeddings(texts)

    @classmethod
    def _get_huggingface_embeddings(cls, texts: List[str]) -> List[List[float]]:
        try:
            from sentence_transformers import SentenceTransformer
            # Lazy load the SentenceTransformer model to optimize memory on boot
            model = SentenceTransformer(settings.HUGGINGFACE_EMBEDDING_MODEL)
            # Encode returns numpy arrays, convert to list of floats
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
            
        except ImportError:
            print("[Embedding] sentence-transformers package not installed. Falling back to mock embeddings.")
            return cls._get_mock_embeddings(texts)
        except Exception as e:
            print(f"[Embedding] HuggingFace embedding failed: {e}. Falling back to mock embeddings.")
            return cls._get_mock_embeddings(texts)

    @classmethod
    def _get_mock_embeddings(cls, texts: List[str], dimension: int = 1536) -> List[List[float]]:
        """
        Generates deterministic, L2-normalized mock embeddings for testing.
        Normalized embeddings ensure cosine similarity matches the mathematical dot product.
        """
        results = []
        for text in texts:
            # Hash text to seed generator deterministically
            h = hashlib.sha256(text.encode("utf-8")).hexdigest()
            seed = int(h, 16) % (2**32)
            
            # Generate deterministic floats using seeded random generator
            rng = random.Random(seed)
            vector = [rng.uniform(-1, 1) for _ in range(dimension)]
            
            # Normalize vector to unit length (L2 norm = 1.0)
            norm = sum(x*x for x in vector) ** 0.5
            normalized_vector = [x / norm for x in vector] if norm > 0 else vector
            results.append(normalized_vector)
            
        return results
