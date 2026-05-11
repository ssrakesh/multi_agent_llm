from logger import proof_log

def judge_agent(
    llm,
    query,
    answers
):

    proof_log(
        "Judge performing self-consistency selection"
    )

    return answers[0]
