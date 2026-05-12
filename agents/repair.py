import json

from logger import pipeline_log


def _repair_bad_clip(blob, limit):

    s = str(blob).strip()

    if len(s) <= limit:

        return s

    return (
        s[:limit]
        + "\n…_(repair: truncated malformed output — do not imitate this tail)_"
    )


class RepairAgent:

    @staticmethod
    def repair(
        llm,
        bad_output,
        error_message,
        *,
        query,
        natural_answer,
        used_tool,
        used_rag,
    ):

        from config import (
            MAX_REPAIR_BAD_OUTPUT_CHARS,
            MAX_REPAIR_SOURCE_NATURAL_CHARS,
            MAX_STRUCTURED_REPAIR_TOKENS,
            REPAIR_JSON_PROMPT,
            STRUCTURED_REPEAT_PENALTY,
            STRUCTURED_TEMPERATURE,
        )

        pipeline_log(
            "REPAIR",
            "Invoking structured-output repair generation.",
        )

        nat = _repair_bad_clip(
            str(natural_answer),
            MAX_REPAIR_SOURCE_NATURAL_CHARS,
        )

        bd = _repair_bad_clip(bad_output, MAX_REPAIR_BAD_OUTPUT_CHARS)

        prompt = REPAIR_JSON_PROMPT.format(
            query=query,
            natural_answer=nat,
            used_tool=json.dumps(bool(used_tool)),
            used_rag=json.dumps(bool(used_rag)),
            error=str(error_message)[:2048],
            bad_output=bd,
        )

        return llm.generate(
            prompt,
            max_tokens=MAX_STRUCTURED_REPAIR_TOKENS,
            temperature=STRUCTURED_TEMPERATURE,
            repeat_penalty=STRUCTURED_REPEAT_PENALTY,
            log_full_prompt=True,
        )
