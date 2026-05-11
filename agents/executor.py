class StructuredOutputAgent:

    @staticmethod
    def generate_json(
        query,
        answer
    ):

        return {
            "query": query,
            "answer": answer
        }
