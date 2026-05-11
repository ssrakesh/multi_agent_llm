import json
from schema import OutputSchema

class Validator:

    @staticmethod
    def validate(output_text):

        try:
            parsed = json.loads(output_text)

            validated = OutputSchema(**parsed)

            return validated, True

        except Exception as e:
            return str(e), False
