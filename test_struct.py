import json
import sys
from llm import LLM
from agents.validator import Validator
from schema import OutputSchema

# Import everything from config
from config import (
    AGENT_MODELS,
    STRUCTURED_JSON_PROMPT,
    MAX_STRUCTURED_NATURAL_CHARS,
    MAX_STRUCTURED_LLM_TOKENS,
    STRUCTURED_TEMPERATURE,
    STRUCTURED_REPEAT_PENALTY,
)

def test_structured():
    """Test structured output using the exact STRUCTURED_JSON_PROMPT from config."""
    print("\n" + "=" * 70)
    print("TESTING STRUCTURED OUTPUT (using actual STRUCTURED_JSON_PROMPT from config)")
    print("=" * 70)

    query = "A student asks: 'Does the Eiffel Tower stand in Berlin, and does water boil at 90°C everywhere?' Use retrieval to give the correct facts, then explain when a travel chatbot should retrieve facts instead of relying on its training memory."
    natural_answer = "No, the Eiffel Tower is in Paris, France. Water boils at 100°C at sea level. A travel chatbot should retrieve facts when the question involves specific, verifiable details not in its training data."
    used_tool = False
    used_rag = True

    prompt = STRUCTURED_JSON_PROMPT.format(
        query=query,
        natural_answer=natural_answer[:MAX_STRUCTURED_NATURAL_CHARS],
        used_tool=json.dumps(bool(used_tool)),
        used_rag=json.dumps(bool(used_rag)),
    )

    print(f"Prompt length: {len(prompt)} chars")
    print("\n--- Prompt (first 500 chars) ---")
    print(prompt[:500])
    print("...\n")

    model_path = AGENT_MODELS.get("structured", AGENT_MODELS.get("planner"))
    print(f"Loading structured model: {model_path}")
    llm = LLM(model_path)

    raw = llm.generate(
        prompt,
        max_tokens=MAX_STRUCTURED_LLM_TOKENS,
        temperature=STRUCTURED_TEMPERATURE,
        repeat_penalty=STRUCTURED_REPEAT_PENALTY,
    )
    print(f"\n--- Raw output ---\n{raw}\n")

    blob = Validator.extract_json_object(raw)
    if blob:
        try:
            data = json.loads(blob)
            # Validate against Pydantic schema
            OutputSchema.model_validate(data)
            print("✓ Valid JSON matches OutputSchema")
            print(f"  query: {data['query'][:60]}...")
            print(f"  answer: {data['answer'][:60]}...")
            print(f"  used_tool: {data['used_tool']}")
            print(f"  used_rag: {data['used_rag']}")
        except Exception as e:
            print(f"✗ Validation error: {e}")
    else:
        print("✗ No JSON object extracted")
    llm.unload()
test_structured()