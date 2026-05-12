from logger import pipeline_log


def judge_agent(query, answers, enabled=True):

    if not enabled:

        pipeline_log(
            "JUDGE",
            "Self-consistency disabled — using planner trajectory only.",
        )

        return answers[0]

    pipeline_log(
        "JUDGE",
        "Comparing planner vs executor answers (keyword grounding preference).",
    )

    for idx, a in enumerate(answers, start=1):

        txt = str(a).lower()

        if (
            "online_api" in txt
            or
            "retrieval" in txt
            or
            "grounding" in txt
        ):

            pipeline_log(
                "JUDGE",
                f"Selected trajectory #{idx}: matched grounding/external signal.",
            )

            return a

    pipeline_log(
        "JUDGE",
        "Fallback: trajectory #1 (no grounding keyword tie-break).",
    )

    return answers[0]
