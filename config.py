from pathlib import Path


_ROOT = Path(__file__).resolve().parent


REPORTS_DIR = _ROOT / "reports"


EVALUATION_REPORT_PATH = REPORTS_DIR / "evaluation_report.md"


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
    "structured": (
        "models/Phi-4-mini-reasoning-GGUF/"
        "Phi-4-mini-reasoning-Q4_K_M.gguf"
    ),
}

MAX_NEW_TOKENS = 128

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

MAX_JSON_REPAIR_ATTEMPTS = 2

# Benchmark: SLM JSON + validator/repair runs for every dataset row unless
# that row sets "structured_eval": false (lighter-faster checks).
DEFAULT_STRUCTURED_LLM_EVAL = True


REACT_PHASE1_PROMPT = """You are the {role} in a Thought->Action->Observation ReAct workflow.
Analyze the QUESTION briefly, then reply with ONLY a single JSON object (no prose, no markdown fences):
{{"thought":"<one sentence>","action":"<weather|rag|none>"}}
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

Write a concise final answer for the user.
"""

STRUCTURED_JSON_PROMPT = """You output ONLY valid JSON for a downstream API. No markdown, no commentary.
Required keys with exact typing: query (string), answer (string), used_tool (boolean), used_rag (boolean).

Copy QUERY verbatim into the "query" field. Place the natural answer in "answer".

QUERY:
{query}

NATURAL_ANSWER:
{natural_answer}

FLAGS (must match booleans):
used_tool={used_tool}
used_rag={used_rag}
"""

REPAIR_JSON_PROMPT = """The prior output was invalid JSON for the schema
{{query:str,answer:str,used_tool:bool,used_rag:bool}}.

ERROR:
{error}

BAD OUTPUT:
{bad_output}

Respond with ONLY a corrected JSON object, no fences.
"""

PLANNER_PROMPT = """
You are a planning agent coordinating reasoning before external actions.
"""

EXECUTOR_PROMPT = """
You are a factual executor agent.
Prioritize external evidence and grounded reasoning.
"""

JUDGE_PROMPT = """
You are a judge agent.
Prefer grounded and tool-supported answers.
"""
