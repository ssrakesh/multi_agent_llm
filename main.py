from pipeline import MultiAgentPipeline
from rag import RAGSystem
from tools import (
    weather_tool,
    python_tool,
    kb_lookup_tool
)
from evaluation import Evaluator

kb = [
    "KV cache reduces autoregressive recomputation.",
    "Quantization reduces VRAM usage.",
    "RAG reduces hallucinations.",
    "Self-consistency improves reasoning robustness.",
    "Tool restraint avoids unnecessary API calls."
]

TOOLS = {
    "weather": weather_tool,
    "python": python_tool,
    "kb_lookup": lambda q:
        kb_lookup_tool(q, kb)
}

rag = RAGSystem()

pipeline = MultiAgentPipeline(
    TOOLS,
    rag
)

evaluator = Evaluator(
    pipeline
)

evaluator.evaluate(
    "inputs.json"
)
