from prompts import JUDGE_PROMPT

def judge_agent(
    llm,
    query,
    candidate_answers
):

    answers = ""

    for idx, ans in enumerate(candidate_answers):
        answers += f"Answer {idx+1}:\n{ans}\n\n"

    prompt = JUDGE_PROMPT.format(
        query=query,
        answers=answers
    )

    result = llm.generate(prompt)

    return result["text"]
