from logger import proof_log

def judge_agent(query, answers):

    proof_log(
        "Judge comparing trajectories"
    )

    for a in answers:

        txt = str(a).lower()

        if (
            "online_api" in txt
            or
            "retrieval" in txt
            or
            "grounding" in txt
        ):
            return a

    return answers[0]
