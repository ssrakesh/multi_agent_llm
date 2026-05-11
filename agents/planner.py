import re

from prompts import SYSTEM_PROMPT

from logger import (
    proof_log,
    stage_log,
    sys_log
)


# ============================================================
# PARSE REACT RESPONSE
# ============================================================

def parse_response(response):

    # --------------------------------------------------------
    # FINAL ANSWER
    # --------------------------------------------------------

    final_match = re.search(
        r"FINAL:\\s*(.*)",
        response,
        re.DOTALL
    )

    if final_match:

        return {
            "type": "final",
            "answer": (
                final_match
                .group(1)
                .strip()
            )
        }

    # --------------------------------------------------------
    # ACTION
    # --------------------------------------------------------

    action_match = re.search(
        r"ACTION:\\s*(.*)",
        response
    )

    input_match = re.search(
        r"INPUT:\\s*(.*)",
        response
    )

    if action_match:

        return {
            "type": "action",
            "tool": (
                action_match
                .group(1)
                .strip()
            ),
            "input": (
                input_match
                .group(1)
                .strip()
                if input_match
                else ""
            )
        }

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    return {
        "type": "unknown"
    }


# ============================================================
# MAIN REACT AGENT
# ============================================================

def run_react_agent(
    llm,
    query,
    tools,
    rag_system,
    max_steps
):

    stage_log(
        "PLANNER",
        "Starting ReAct reasoning loop"
    )

    proof_log(
        "Planner agent activated"
    )

    history = (
        f"Question: {query}\n"
    )

    used_tool = False
    used_rag = False

    selected_tools = []

    # ========================================================
    # MULTI-STEP REASONING
    # ========================================================

    for step in range(max_steps):

        stage_log(
            "PLANNER",
            f"Reasoning step {step+1}"
        )

        prompt = (
            SYSTEM_PROMPT +
            "\n" +
            history
        )

        # ====================================================
        # GENERATE RESPONSE
        # ====================================================

        response = llm.generate(
            prompt
        )

        print("\n[MODEL RESPONSE]\n")
        print(response)

        parsed = parse_response(
            response
        )

        # ====================================================
        # FINAL ANSWER
        # ====================================================

        if parsed["type"] == "final":

            proof_log(
                "Agent produced final answer"
            )

            return {
                "answer": parsed["answer"],
                "used_tool": used_tool,
                "used_rag": used_rag,
                "selected_tools": (
                    selected_tools
                ),
                "trajectory": history
            }

        # ====================================================
        # TOOL EXECUTION
        # ====================================================

        elif parsed["type"] == "action":

            tool = parsed["tool"]
            tool_input = parsed["input"]

            selected_tools.append(
                tool
            )

            stage_log(
                "TOOL",
                f"Selected tool -> {tool}"
            )

            proof_log(
                f"Tool invocation detected: {tool}"
            )

            observation = ""

            # ------------------------------------------------
            # RAG TOOL
            # ------------------------------------------------

            if tool == "rag":

                used_rag = True

                proof_log(
                    "RAG grounding activated"
                )

                observation = (
                    rag_system.retrieve(
                        tool_input
                    )
                )

            # ------------------------------------------------
            # WEATHER TOOL
            # ------------------------------------------------

            elif tool == "weather":

                used_tool = True

                proof_log(
                    "External weather tool used"
                )

                observation = tools[
                    "weather"
                ](tool_input)

            # ------------------------------------------------
            # PYTHON TOOL
            # ------------------------------------------------

            elif tool == "python":

                used_tool = True

                proof_log(
                    "Python execution tool used"
                )

                observation = tools[
                    "python"
                ](tool_input)

            # ------------------------------------------------
            # KB LOOKUP
            # ------------------------------------------------

            elif tool == "kb_lookup":

                used_tool = True

                proof_log(
                    "Knowledge base lookup used"
                )

                observation = tools[
                    "kb_lookup"
                ](tool_input)

            # ------------------------------------------------
            # TOOL RESTRAINT
            # ------------------------------------------------

            else:

                proof_log(
                    "Unknown tool avoided"
                )

                observation = (
                    "Unknown tool"
                )

            print("\n[OBSERVATION]\n")
            print(observation)

            # =================================================
            # APPEND OBSERVATION
            # =================================================

            history += (
                response +
                "\n" +
                f"OBSERVATION: "
                f"{observation}\n"
            )

        # ====================================================
        # NO TOOL SELECTED
        # ====================================================

        else:

            proof_log(
                "No valid tool selected"
            )

            history += (
                response +
                "\n"
            )

    # ========================================================
    # FAILED
    # ========================================================

    proof_log(
        "Agent failed to complete reasoning"
    )

    return {
        "answer": "FAILED",
        "used_tool": used_tool,
        "used_rag": used_rag,
        "selected_tools": (
            selected_tools
        ),
        "trajectory": history
    }