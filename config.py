from pathlib import Path


_ROOT = Path(__file__).resolve().parent


REPORTS_DIR = _ROOT / "reports"


EVALUATION_REPORT_PATH = REPORTS_DIR / "evaluation_report.md"


# Report fidelity: ``None`` = never truncate narratives, RAG text, telemetry JSON,
# or ReAct traces (markdown files may become very large).
EVAL_REPORT_BODY_CHAR_CAP = None

EVAL_REPORT_REACT_TRACE_LINES = None


STATES_DIR = _ROOT / "states"


AGENT_MODELS = {
    # "planner": (
    #     "models/Phi-3-mini-4k-instruct-gguf/"
    #     "Phi-3-mini-4k-instruct-q4.gguf"
    # ),
    # "executor": (
    #     "models/gemma-2-2b-it-GGUF/"
    #     "gemma-2-2b-it-Q5_K_M.gguf"
    # ),
    # "judge": (
    #     "models/Mistral-7B-Instruct-v0.3-GGUF/"
    #     "Mistral-7B-Instruct-v0.3-Q4_K_M.gguf"
    # ),
    # "structured": (
    #     "models/Phi-3-mini-4k-instruct-gguf/"
    #     "Phi-3-mini-4k-instruct-q4.gguf"
    # ),
    # Strong reasoning + decomposition for planning tasks
    "planner": (
        "models/Phi-4-mini-reasoning-GGUF/"
        "Phi-4-mini-reasoning-Q4_K_M.gguf"
    ),

    # Better grounded answering and RAG integration
    "executor": (
        "models/gemma-4-E4B-it-GGUF/"
        "gemma-4-E4B-it-Q4_K_M.gguf"
    ),

    # Lightweight and fast for trajectory comparison/self-consistency
    "judge": (
        "models/Qwen3.5-2B-GGUF/"
        "Qwen3.5-2B-Q4_K_M.gguf"
    ),

    # Stable JSON and structured output generation
    # "structured": (
    #     "models/Phi-4-mini-reasoning-GGUF/"
    #     "Phi-4-mini-reasoning-Q4_K_M.gguf"
    # ),
    # use non‑reasoning model to avoid toomany replay in think block in reasoning phi4 model.
    "structured": (
        "models/Phi-3-mini-4k-instruct-gguf/"
        "Phi-3-mini-4k-instruct-q4.gguf"
    ),
}
MAX_CONTEXT_TOKENS = 8192

MAX_NEW_TOKENS = 128

# ReAct phase-1 is a single JSON blob; phase-2 must answer substantively — the same
# 128-token cap as chat caused placeholder answers ("ANSWER: RESPONSE") and empty
# executor completions while single-pass baseline used BASELINE_PROMPT + 512 tokens.
MAX_REACT_JSON_TOKENS = 320

MAX_REACT_SYNTHESIS_TOKENS = 896

# Structured conformance + repair (JSON object + possible reasoning preamble).
MAX_STRUCTURED_LLM_TOKENS = 1152

# Single-pass baseline: raw `query` alone often yields **empty** completions from
# instruction/reasoning GGUFs via llama.cpp; wrap + allow more budget than agents.
BASELINE_PROMPT_TEMPLATE = """You are a helpful assistant answering an evaluation question.

Give a direct, substantive answer (no refusal). Use concise technical wording.

Question:
{query}

Answer:
"""

MAX_BASELINE_NEW_TOKENS = 512

TEMPERATURE = 0.3

TOP_P = 0.9

STRUCTURED_TEMPERATURE = 0.12

STRUCTURED_REPEAT_PENALTY = 1.15

MAX_STRUCTURED_NATURAL_CHARS = 8096

MAX_REPAIR_SOURCE_NATURAL_CHARS = 6000

MAX_REPAIR_BAD_OUTPUT_CHARS = 1200

MAX_STRUCTURED_REPAIR_TOKENS = 640

# giving more chances to recover from malformed JSON (e.g. due to LLM preambles, trailing commentary, or partial generation) before conceding failure and logging an error.
MAX_JSON_REPAIR_ATTEMPTS = 4

# Benchmark: SLM JSON + validator/repair runs for every dataset row unless
# that row sets "structured_eval": false (lighter-faster checks).
DEFAULT_STRUCTURED_LLM_EVAL = True

REACT_PHASE1_PROMPT = """You are the {role} in a Thought->Action->Observation ReAct workflow.
Analyze the QUESTION briefly, then reply with ONLY a single JSON object (no prose, no markdown fences).

Example:
{{"thought": "The user asks for live weather data, so I need to call the weather tool.", "action": "weather"}}

Rules:
- "weather": user wants a live/current weather observation for deciding real-world behaviour (forecast, umbrella, today's conditions).
- "rag": factual grounding from a knowledge corpus helps (topics like hallucinations, RAG, KV cache, quantization, transformer misconceptions).
- "none": no external tool or retrieval is needed (e.g. pure coding tasks, API design questions without asking for live data).

QUESTION:
{query}
"""

REACT_PHASE2_PROMPT = """{base_prompt}
You must answer after reviewing observations from tools or retrieval.

QUESTION:
{query}

OBSERVATIONS (may be empty):
{observations}

Write a concise final answer for the user. Prefer reusing factual phrases from the question and OBSERVATIONS (exact wording when helpful).
"""

STRUCTURED_JSON_PROMPT = """You output ONLY one JSON object for a downstream parser. Breaking these rules corrupts downstream systems:

Rules:
- First non-whitespace character must be {{ and the last non-whitespace must be }} — nothing before or after.
- The "answer" value must be a non‑empty string.
- No markdown, no code fences/backticks, no "Final Answer" headers, no LaTeX or \\boxed{{}} or \\text{{}} anywhere.
- The "answer" value must be a single UTF-8 string of plain explanatory prose — compress NATURAL_ANSWER into coherent text once (no repetitions).

Required keys and types exactly: "query" (string), "answer" (string), "used_tool" (boolean), "used_rag" (boolean).
Use DOUBLE quotes for all JSON keys and string values only.

Example shape (substitute values):
{{"query":"...","answer":"...","used_tool":false,"used_rag":false}}

QUERY (copy verbatim into "query"):
{query}

NATURAL_ANSWER (transcribe once into plain "answer"):
{natural_answer}

FLAGS ("used_tool"/"used_rag" booleans MUST match exactly):
used_tool={used_tool}
used_rag={used_rag}
"""

REPAIR_JSON_PROMPT = """Rebuild EXACTLY one compact JSON object for this schema fields:
{{"query": string, "answer": string, "used_tool": boolean, "used_rag": boolean}}

Rules:
- First character {{ last character }}. No preamble, fences, bullets, repetition, Final Answer fragments, \\boxed{{}}, or prose outside JSON.
- Remove any prefix like ‘ANSWER:’ or ‘Final answer:’ and ensure the first character is {{.

SOURCE OF TRUTH (do not hallucinate unrelated content):
- Copy "query" VERBATIM from QUERY below (including punctuation).
- Set "answer" to a single SHORT plain-text synopsis of NATURAL_ANSWER (strip markup/LaTeX/fences/novelty tokens; NEVER repeat paragraphs).
- Set booleans exactly as FLAGS states.

QUERY:
{query}

NATURAL_ANSWER:
{natural_answer}

FLAGS:
used_tool={used_tool}
used_rag={used_rag}

ERROR:
{error}

BAD OUTPUT:
{bad_output}
"""

PLANNER_PROMPT = """
You are a planning agent coordinating reasoning before external actions.
"""

EXECUTOR_PROMPT = """
You are a factual executor agent.
Prioritize external evidence and grounded reasoning.
"""

USE_LLM_JUDGE = True

MAX_JUDGE_NEW_TOKENS = 320

JUDGE_TEMPERATURE = 0.15

JUDGE_LLM_PROMPT = """{base_judge}

Pick the better answer for the user question. Prefer factually grounded, specific, non-refusal text.
If one answer is a meta-instruction (e.g. "your answer should include…") and the other is substantive, pick the substantive one.
If retrieval/tool context was used ({rag_note}), slightly prefer the answer that uses that evidence appropriately.

Return ONLY one JSON object (no markdown fences, no commentary), for example:
{{"choice":"executor","reason":"The executor answer cites retrieved evidence more directly."}}
Optional: {{"choice":"planner","reason":"one short phrase"}}
Your entire response must start with {{ and end with }}.

QUESTION:
{query}

OBSERVATION / TOOL HINTS (may be empty):
{hints}

ANSWER_PLANNER (trajectory 1):
{planner}

ANSWER_EXECUTOR (trajectory 2):
{executor}
"""

JUDGE_PROMPT = """
You are a judge agent comparing two candidate answers to the same user question.
Be concise and decisive; output only the requested JSON decision object.
"""
