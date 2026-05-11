from prompts import REPAIR_PROMPT

class RepairAgent:

    @staticmethod
    def repair(llm, bad_json, error):

        prompt = REPAIR_PROMPT.format(
            error=error,
            bad_json=bad_json
        )

        result = llm.generate(prompt)

        return result["text"]
