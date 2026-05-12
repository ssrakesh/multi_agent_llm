from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class RAGSystem:

    def __init__(self, path="data/knowledge_base.txt"):

        self.embedder = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        with open(path, encoding="utf-8") as f:

            self.docs = [
                x.strip()
                for x in f.readlines()
                if x.strip()
            ]

        emb = self.embedder.encode(
            self.docs,
            convert_to_numpy=True
        )

        self.index = faiss.IndexFlatL2(
            emb.shape[1]
        )

        self.index.add(
            emb.astype(np.float32)
        )

    def retrieve(self, query, top_k=3):

        q = self.embedder.encode(
            [query],
            convert_to_numpy=True
        )

        _, idx = self.index.search(
            q.astype(np.float32),
            top_k
        )

        return "\n".join(
            [self.docs[i] for i in idx[0]]
        )
