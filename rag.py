from sentence_transformers import SentenceTransformer

import faiss

import numpy as np

from logger import error_log


class RAGSystem:

    def __init__(self, path="data/knowledge_base.txt"):

        self.embedder = SentenceTransformer(
            "all-MiniLM-L6-v2",
        )

        try:

            with open(path, encoding="utf-8") as fh:

                self.docs = [
                    ln.strip()
                    for ln in fh.readlines()
                    if ln.strip()
                ]

        except OSError as exc:

            error_log(
                (
                    "RAG knowledge file missing or cannot be opened — "
                    f"{path!r}"
                ),
                exc,
            )

            raise

        emb = (
            self.embedder.encode(
                self.docs,
                convert_to_numpy=True,
            )
        )

        self.index = faiss.IndexFlatL2(
            emb.shape[1],
        )

        self.index.add(
            emb.astype(np.float32),
        )

    def retrieve(self, query, top_k=3):

        q = self.embedder.encode(
            [query],
            convert_to_numpy=True,
        )

        _, idx = self.index.search(
            q.astype(np.float32),
            top_k,
        )

        return "\n".join(
            [
                self.docs[i]
                for i in idx[0]
            ],
        )
