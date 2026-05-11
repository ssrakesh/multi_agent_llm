# use manauly downloaded GGUF models for better performance and to avoid issues with Hugging Face's transformers library. 

AGENT_MODELS = {
    "planner":"models/Phi-3-mini-4k-instruct-gguf/Phi-3-mini-4k-instruct-q4.gguf",
    "executor":"models/gemma-2-2b-it-GGUF/gemma-2-2b-it-Q5_K_M.gguf",
    "judge":"models/Mistral-7B-Instruct-v0.3-GGUF/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf"
}

MAX_AGENT_STEPS = 3
MAX_NEW_TOKENS = 128
TEMPERATURE = 0.7
TOP_P = 0.9
