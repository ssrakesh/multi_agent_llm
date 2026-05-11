from pipeline import MultiAgentPipeline
from rag import RAGSystem
from tools import kb_lookup_tool, python_tool

knowledge_base = [
    "Transformers use self-attention.",
    "KV cache improves inference efficiency.",
    "RAG retrieves external knowledge."
]

TOOLS = {
    "kb_lookup": lambda q: kb_lookup_tool(
        q,
        knowledge_base
    ),
    "python": python_tool
}

rag_system = RAGSystem()

pipeline = MultiAgentPipeline(
    TOOLS,
    rag_system
)

query = "Explain KV cache optimization"

result = pipeline.run(query)

print(result)
