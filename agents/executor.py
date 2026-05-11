from prompts import JSON_PROMPT

class StructuredOutputAgent:

    @staticmethod
    def generate_json(
        llm,
        query,
        answer,
        used_tool,
        used_rag
    ):

        prompt = JSON_PROMPT.format(
            query=query,
            answer=answer
        )

        prompt += (
            f"\nused_tool={used_tool}"
            f"\nused_rag={used_rag}"
        )

        result = llm.generate(prompt)

        return result["text"]
