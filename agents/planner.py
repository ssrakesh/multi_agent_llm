from logger import (
    proof_log,
    stage_log
)

def run_react_agent(
    llm,
    query,
    tools,
    rag_system,
    prompt_template
):

    observations = []

    used_tool = False
    used_rag = False

    if "weather" in query.lower():

        stage_log(
            "TOOL",
            "Weather tool selected"
        )

        obs = tools["weather"](
            "Bengaluru"
        )

        observations.append(obs)

        used_tool = True

    elif (
        "hallucination" in query.lower()
        or
        "kv cache" in query.lower()
        or
        "quantization" in query.lower()
    ):

        stage_log(
            "RAG",
            "Retrieval grounding selected"
        )

        obs = rag_system.retrieve(query)

        observations.append(obs)

        used_rag = True

    proof_log(
        "Reasoning trajectory generated"
    )

    history = (
        f"Question: {query}\n"
        f"Observations: {observations}"
    )

    response = llm.generate(
        prompt_template +
        "\n" +
        history
    )

    return {
        "answer": response,
        "used_tool": used_tool,
        "used_rag": used_rag,
        "observations": observations
    }
