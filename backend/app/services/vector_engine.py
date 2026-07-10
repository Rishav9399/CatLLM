import uuid
import logging
from typing import List, Dict, Any, Tuple
from collections import Counter
import re
import asyncio  # ARCHITECTURAL ADDITION: For event loop offloading

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
# pyrefly: ignore [missing-import]
from sentence_transformers import SentenceTransformer, CrossEncoder
# pyrefly: ignore [missing-import]
from fastembed import SparseTextEmbedding  # ARCHITECTURAL UPGRADE: SPLADE/BM25 Support

logger = logging.getLogger(__name__)

class EnterpriseVectorEngine:
    """
    The Hybrid Retrieval & Re-ranking Cortex.
    Implements a 3-Stage production retrieval funnel:
    1. Parallel Retrieval (Dense + Sparse)
    2. Reciprocal Rank Fusion (RRF)
    3. Cross-Encoder Re-ranking
    """
    def __init__(self, collection_name: str = "enterprise_knowledge"):
        self.collection_name = collection_name
        
        # 1. Connect to Qdrant (Local disk mode for persistence)
        # In production, change path to a cloud URL.
        self.client = QdrantClient(path="./qdrant_storage")
        
        # 2. AI Model Placeholders (Singleton Pattern)
        self.dense_model = None
        self.cross_encoder = None
        self.sparse_model = None # The new SPLADE model
        
        # We use a lightweight dense model perfect for 4GB VRAM (GTX 1650)
        # BAAI/bge-small-en-v1.5 has 384 dimensions and is blisteringly fast.
        self.dense_model_name = "BAAI/bge-small-en-v1.5"
        self.dense_dim = 384 
        
        # The Re-ranker. Reads Query + Text simultaneously.
        self.cross_encoder_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        
        # SPLADE creates highly optimized, semantically-aware sparse vectors
        self.sparse_model_name = "prithivida/Splade_PP_en_v1"
        
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Sets up the Hybrid HNSW Graph in the Vector DB."""
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": qmodels.VectorParams(
                        size=self.dense_dim,
                        distance=qmodels.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    # Configures Qdrant to accept our lexical/keyword indices
                    "sparse": qmodels.SparseVectorParams() 
                }
            )
            logger.info(f"Initialized Hybrid HNSW Collection: {self.collection_name}")

    def _load_models(self):
        """
        Lazy-loads models into VRAM. 
        This prevents the FastAPI startup from hanging and manages GPU memory tightly.
        """
        if self.dense_model is None:
            logger.info("Loading Dense Embedding Model into VRAM...")
            self.dense_model = SentenceTransformer(self.dense_model_name)
            
        if self.sparse_model is None:
            logger.info("Loading SPLADE Sparse Model into VRAM...")
            self.sparse_model = SparseTextEmbedding(model_name=self.sparse_model_name)
            
        if self.cross_encoder is None:
            logger.info("Loading Cross-Encoder Re-ranker into VRAM...")
            self.cross_encoder = CrossEncoder(self.cross_encoder_name)

    def ingest_chunks(self, chunks: List[Dict[str, Any]]):
        """
        The Encoding Factory. Converts our text chunks into math and upserts them.
        """
        if not chunks:
            return

        self._load_models()
        points = []
        
        # Batch extract all texts for fast GPU processing
        texts = [chunk["content"] for chunk in chunks]
        
        # 1. Generate Dense Vectors in one massive GPU batch
        dense_vectors = self.dense_model.encode(texts).tolist()
        
        # 2. Generate SPLADE Sparse Vectors in one massive batch
        # fastembed returns a generator, we cast to list
        sparse_vectors = list(self.sparse_model.embed(texts))
        
        for idx, chunk in enumerate(chunks):
            # Extract the SPLADE indices and weights
            sparse_indices = sparse_vectors[idx].indices.tolist()
            sparse_values = sparse_vectors[idx].values.tolist()
            
            # 3. Create the multi-vector payload
            point = qmodels.PointStruct(
                id=str(chunk["id"]), # Critical: Binds Vector ID to PostgreSQL UUID
                vector={
                    "dense": dense_vectors[idx],
                    "sparse": qmodels.SparseVector(
                        indices=sparse_indices, 
                        values=sparse_values
                    )
                },
                # Storing metadata for fast pre-filtering (e.g., "Only search CODE chunks")
                payload={
                    "chunk_type": chunk["chunk_type"],
                    "document_id": str(chunk["document_id"]),
                    "content": chunk["content"] # We store content here temporarily for the Cross-Encoder
                }
            )
            points.append(point)
            
        # 4. Atomic Upsert to HNSW Graph
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Successfully vectorized and indexed {len(chunks)} chunks.")

    # ARCHITECTURAL UPGRADE: Changed to an async function to allow non-blocking thread offloading
    async def hybrid_search_funnel(self, query: str, top_k: int = 5, filter_kwargs: dict = None) -> List[Dict[str, Any]]:
        """
        THE STRICT FUNNEL ARCHITECTURE.
        Finds the absolute best chunks without hallucination, completely non-blocking.
        """
        self._load_models()
        
        # --- STAGE 1: PARALLEL RETRIEVAL (The Wide Net) ---
        # Offload blocking Dense inference to a background thread!
        query_dense_np = await asyncio.to_thread(self.dense_model.encode, query)
        query_dense = query_dense_np.tolist()
        
        # Get SPLADE query vector (also offloaded)
        query_sparse_gen = await asyncio.to_thread(lambda q: list(self.sparse_model.embed([q])), query)
        query_sparse = query_sparse_gen[0]
        query_sparse_indices = query_sparse.indices.tolist()
        query_sparse_values = query_sparse.values.tolist()
        
        prefetch_limit = 40

        # Execute dense search via the modern query_points API
        # Offloaded to a thread — QdrantClient is synchronous/blocking
        async def _dense_search():
            return await asyncio.to_thread(
                self.client.query_points,
                collection_name=self.collection_name,
                query=query_dense,
                using="dense",
                limit=prefetch_limit,
                with_payload=True
            )

        async def _sparse_search():
            if not query_sparse_indices:
                return None
            return await asyncio.to_thread(
                self.client.query_points,
                collection_name=self.collection_name,
                query=qmodels.SparseVector(
                    indices=query_sparse_indices,
                    values=query_sparse_values
                ),
                using="sparse",
                limit=prefetch_limit,
                with_payload=True
            )

        # Run both searches in parallel — same wall-clock time as the old search_batch
        dense_result, sparse_result = await asyncio.gather(_dense_search(), _sparse_search())

        dense_hits = dense_result.points if dense_result else []
        sparse_hits = sparse_result.points if sparse_result else []


        # --- STAGE 2: RECIPROCAL RANK FUSION (RRF) ---
        # Equalizes Cosine Distance (Dense) with TF/BM25 counts (Sparse)
        rrf_scores: Dict[str, dict] = {}
        k_constant = 60 # Standard damping factor
        
        # Process Dense ranks
        for rank, hit in enumerate(dense_hits):
            if hit.id not in rrf_scores:
                rrf_scores[hit.id] = {"score": 0.0, "payload": hit.payload}
            rrf_scores[hit.id]["score"] += 1.0 / (k_constant + rank + 1)
            
        # Process Sparse ranks
        for rank, hit in enumerate(sparse_hits):
            if hit.id not in rrf_scores:
                rrf_scores[hit.id] = {"score": 0.0, "payload": hit.payload}
            rrf_scores[hit.id]["score"] += 1.0 / (k_constant + rank + 1)
            
        # Sort by RRF score. Keep the Top 15 candidates.
        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1]["score"], reverse=True)[:15]
        
        if not sorted_candidates:
            return []

        # --- STAGE 3: THE CROSS-ENCODER (The Sniper) ---
        # The Bi-Encoders cast a wide net. Now, the Cross-Encoder reads the Query and Candidate 
        # AT THE SAME TIME. It is highly accurate, but computationally heavy.
        
        # Prepare pairs for the model: [ [Query, Chunk_1], [Query, Chunk_2], ... ]
        candidate_pairs = []
        for candidate_id, data in sorted_candidates:
            candidate_pairs.append([query, data["payload"]["content"]])
            
        # THE FIX: Offload the heavy N^2 neural network calculation so we don't starve FastAPI
        cross_scores = await asyncio.to_thread(self.cross_encoder.predict, candidate_pairs)
        
        # Attach the absolute relevance scores back to our candidates
        final_results = []
        for i, (candidate_id, data) in enumerate(sorted_candidates):
            final_results.append({
                "chunk_id": candidate_id,
                "relevance_score": float(cross_scores[i]),
                "content": data["payload"]["content"],
                "metadata": {
                    "chunk_type": data["payload"]["chunk_type"],
                    "document_id": data["payload"]["document_id"]
                }
            })
            
        # THE SORT: Force descending order based on Cross-Encoder logits. 
        # The chunk with the highest semantic match is guaranteed to be at index 0.
        final_results = sorted(final_results, key=lambda x: x["relevance_score"], reverse=True)
        
        return final_results[:top_k]