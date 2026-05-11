AGENT_MODELS = {
    "planner": "microsoft/Phi-3-mini-4k-instruct",
    "executor": "google/gemma-2b-it",
    "judge": "mistralai/Mistral-7B-Instruct-v0.3"
}

MAX_NEW_TOKENS = 128
TEMPERATURE = 0.7
TOP_P = 0.9

MAX_AGENT_STEPS = 4
NUM_DEBATE_AGENTS = 2

USE_4BIT = True

ENABLE_KV_CACHE_PERSISTENCE = True
KV_CACHE_DIR = "kv_cache"
