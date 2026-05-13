import sys
import re
import json


# sys.path.insert(0, ".")

from llm import LLM
from config import AGENT_MODELS, REACT_PHASE1_PROMPT
from tools import weather_tool


# ------------------------------------------------------------------
# 1.  City extraction helper
# ------------------------------------------------------------------
def extract_city_from_query(query: str) -> str:
    """Pull city name from query for dynamic weather tool parameterization."""
    q = query.strip()
    # Prefer "weather in <City>" or "weather for <City>"
    m = re.search(r"weather\s+(?:in|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", q)
    if m:
        return m.group(1)
    # Fallback: first word after "weather" that looks like a proper noun
    m = re.search(r"weather\s+([A-Z][a-z]+)", q)
    if m:
        return m.group(1)
    # Absolute fallback
    return "Bengaluru"


# ------------------------------------------------------------------
# 2.  Strip <think> tags
# ------------------------------------------------------------------
def strip_think_tags(text: str) -> str:
    """Remove reasoning blocks that reasoning models might output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


# ------------------------------------------------------------------
# 3.  Parse the phase‑1 JSON decision
# ------------------------------------------------------------------
def parse_action_from_text(text: str):
    """Return (action, thought, city) or None."""
    text = strip_think_tags(text)
    decoder = json.JSONDecoder()
    idx = text.find("{")
    if idx == -1:
        return None
    try:
        obj, end = decoder.raw_decode(text, idx)
        if isinstance(obj, dict):
            action = obj.get("action", "").lower().strip()
            thought = obj.get("thought", "")
            city = obj.get("city", "").strip() or None
            if action in ("weather", "rag", "none"):
                return action, thought, city
    except json.JSONDecodeError:
        pass
    return None

# ------------------------------------------------------------------
# 4.  Main test for a single query
# ------------------------------------------------------------------
def test_weather_query(query: str):
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"{'='*60}")

    # Load planner model (same as pipeline)
    model_path = AGENT_MODELS["planner"]
    llm = LLM(model_path)

    # Build phase‑1 prompt
    prompt = REACT_PHASE1_PROMPT.format(role="Planner", query=query)
    print("[LLM] Generating phase‑1 action decision...")
    raw_output = llm.generate(prompt, max_tokens=320)

    # Print the raw output (for debugging)
    print(f"[MODEL RAW OUTPUT]\n{raw_output}\n")

    # Parse the decision
    parsed = parse_action_from_text(raw_output)
    if parsed is None:
        print("[WARN] Could not parse JSON action; falling back to heuristic.")
        # Fallback heuristic (same as planner.py)
        ql = query.lower()
        if "weather" in ql and ("today" in ql or "umbrella" in ql or "forecast" in ql):
            action, thought, city = parsed, "Heuristic fallback: live weather intent detected.", None
        else:
            action, thought = "none", "Heuristic fallback: no tool."
    else:
        action = parsed[0]
        thought = parsed[1]
        city = parsed[2]

    print(f"Thought: {thought}")
    print(f"Action : {action}")
    print(f"City : {city}")

    # If action is weather, dynamically extract city and call tool
    if action == "weather":
        
        print(f"\nExtracted city: {city}")
        print("[TOOL] Calling weather_tool...")
        obs = weather_tool(city)
        if "error" in obs:
            print(f"Tool error: {obs['error']}")
        else:
            print(f"Tool response:\n{obs['response']}")
    else:
        print("Action is not 'weather', no tool call made.")

    llm.unload()
    print("\nDone.\n")


# ------------------------------------------------------------------
# 5.  Run tests
# ------------------------------------------------------------------
if __name__ == "__main__":
    test_queries = [
        "What’s the current weather like in London, and should I take an umbrella?",
        "What is today's weather in Bengaluru and should I carry an umbrella?",
        "Tell me the weather in Paris",
    ]
    for q in test_queries:
        test_weather_query(q)