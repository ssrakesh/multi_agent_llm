from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class RAGSystem:

    def __init__(self, path="data/knowledge_base.txt"):

        self.embedder = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        with open(path, "r", encoding="utf-8") as f:
            self.documents = [
                line.strip()
                for line in f.readlines()
                if line.strip()
            ]

        embeddings = self.embedder.encode(
            self.documents,
            convert_to_numpy=True
        )

        self.index = faiss.IndexFlatL2(
            embeddings.shape[1]
        )

        self.index.add(
            embeddings.astype(np.float32)
        )

    def retrieve(self, query, top_k=3):

        query_embedding = self.embedder.encode(
            [query],
            convert_to_numpy=True
        )

        distances, indices = self.index.search(
            query_embedding.astype(np.float32),
            top_k
        )

        results = []

        for idx in indices[0]:
            results.append(self.documents[idx])

        return "\n".join(results)
