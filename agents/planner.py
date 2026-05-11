import re
from prompts import SYSTEM_PROMPT

def parse_agent_response(response):

    final_match = re.search(
        r"FINAL:\s*(.*)",
        response
    )

    if final_match:
        return {
            "type": "final",
            "answer": final_match.group(1)
        }

    action_match = re.search(
        r"ACTION:\s*(.*)",
        response
    )

    input_match = re.search(
        r"INPUT:\s*(.*)",
        response
    )

    if action_match:
        return {
            "type": "action",
            "tool": action_match.group(1).strip(),
            "input": input_match.group(1).strip()
        }

    return {"type": "unknown"}

def run_react_agent(
    llm,
    query,
    tools,
    rag_system,
    max_steps,
    kv_cache=None
):

    history = f"Question: {query}\n"

    used_tool = False
    used_rag = False

    current_cache = kv_cache

    for _ in range(max_steps):

        prompt = SYSTEM_PROMPT + "\n" + history

        result = llm.generate(
            prompt,
            current_cache
        )

        response = result["text"]

        current_cache = result["past_key_values"]

        parsed = parse_agent_response(
            response
        )

        if parsed["type"] == "final":

            return {
                "answer": parsed["answer"],
                "used_tool": used_tool,
                "used_rag": used_rag,
                "past_key_values": current_cache
            }

        if parsed["type"] == "action":

            tool = parsed["tool"]
            tool_input = parsed["input"]

            observation = ""

            if tool == "rag":
                used_rag = True
                observation = rag_system.retrieve(
                    tool_input
                )

            elif tool == "kb_lookup":
                used_tool = True
                observation = tools["kb_lookup"](
                    tool_input
                )

            elif tool == "python":
                used_tool = True
                observation = tools["python"](
                    tool_input
                )

            history += (
                response +
                f"\nOBSERVATION: {observation}\n"
            )

    return {
        "answer": "FAILED",
        "used_tool": used_tool,
        "used_rag": used_rag,
        "past_key_values": current_cache
    }
