from logger import pipeline_log


class RepairAgent:

    @staticmethod
    def repair(llm, bad_output, error_message):

        from config import REPAIR_JSON_PROMPT

        pipeline_log(
            "REPAIR",
            "Invoking structured-output repair generation."
        )

        prompt = REPAIR_JSON_PROMPT.format(
            bad_output=str(bad_output)[:4096],
            error=str(error_message)[:2048],
        )

        return llm.generate(prompt)
