from pipeline import MultiAgentPipeline

from rag import RAGSystem

from tools import (
    weather_tool,
    python_tool,
    kb_lookup_tool,
)

from evaluation import Evaluator

from logger import error_log, section

from config import STATES_DIR


knowledge_base = [
    "KV cache reduces autoregressive recomputation.",
    "Quantization reduces VRAM usage.",
    "RAG reduces hallucinations using retrieval grounding.",
    "Grounding improves factual correctness.",
    "Tool restraint avoids unnecessary API calls.",
]

TOOLS = {
    "weather": weather_tool,
    "python": python_tool,
    "kb_lookup": lambda q: kb_lookup_tool(q, knowledge_base),
}

STATES_DIR.mkdir(parents=True, exist_ok=True)


rag_system = RAGSystem()
pipeline = MultiAgentPipeline(TOOLS, rag_system)
evaluator = Evaluator(pipeline)

section(
    "Course project — benchmark run (Proposal.md / README artefact)",
)

try:

    report_path = evaluator.evaluate(
        "inputs.json",
    )

except Exception as exc:

    error_log(
        "Evaluation run aborted",
        exc,
    )

    raise

print(f"\nReport generated -> {report_path}")
