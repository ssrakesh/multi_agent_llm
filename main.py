from pipeline import MultiAgentPipeline

from rag import RAGSystem

from tools import (
    weather_tool,
    python_tool,
    kb_lookup_tool
)

from evaluation import Evaluator

knowledge_base = [

    "KV cache reduces autoregressive recomputation.",

    "Quantization reduces VRAM usage.",

    "RAG reduces hallucinations using retrieval grounding.",

    "Grounding improves factual correctness.",

    "Tool restraint avoids unnecessary API calls."
]

TOOLS = {

    "weather": weather_tool,

    "python": python_tool,

    "kb_lookup": lambda q:
        kb_lookup_tool(
            q,
            knowledge_base
        )
}

rag_system = RAGSystem()

pipeline = MultiAgentPipeline(
    TOOLS,
    rag_system
)

evaluator = Evaluator(
    pipeline
)

print("\n================================================")
print("FINAL AGENTIC RESEARCH SYSTEM")
print("================================================\n")

evaluator.evaluate(
    "inputs.json"
)

print("\nReport generated -> evaluation_report.md")
