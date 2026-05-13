from llm import LLM
from config import AGENT_MODELS, JUDGE_LLM_PROMPT, MAX_JUDGE_NEW_TOKENS, JUDGE_TEMPERATURE
import json

def extract_json_object(text):
        if not isinstance(text, str):
            text = str(text)
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(text):
            # Find next opening brace
            brace_pos = text.find("{", idx)
            if brace_pos == -1:
                return None
            try:
                obj, end = decoder.raw_decode(text, brace_pos)
                # We only accept dict objects, not lists/strings/numbers
                if isinstance(obj, dict):
                    return text[brace_pos:end]
                # If it parsed something else, move past it
                idx = end
            except json.JSONDecodeError:
                # Could be incomplete or malformed; move past this brace
                idx = brace_pos + 1
        return None

llm = LLM(AGENT_MODELS["judge"])
query = "Does the Eiffel Tower stand in Berlin?"
planner = "No, the Eiffel Tower is in Paris. A travel chatbot should retrieve facts..."
executor = "The Eiffel Tower is in Paris. Water boils at 100°C."
prompt = JUDGE_LLM_PROMPT.format(query=query, planner=planner, executor=executor)
output = llm.generate(prompt, max_tokens=MAX_JUDGE_NEW_TOKENS, temperature=JUDGE_TEMPERATURE, repeat_penalty=1.2)
print("Output from judge LLM:\n")
print(repr(output))
print("Extracted Output from judge LLM:\n")
print(extract_json_object(output))