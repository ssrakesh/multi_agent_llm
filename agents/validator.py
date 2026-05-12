import json
import re

from pydantic import ValidationError

from logger import error_log, validate_log

from schema import OutputSchema


class Validator:

    @staticmethod
    def extract_json_object(text):

        if not isinstance(text, str):

            text = str(text)

        anchored = re.search(
            r"\{\s*\"query\"\s*:",
            text,
        )

        if anchored:

            start = anchored.start()

        else:

            start = text.find("{")

            if start < 0:

                return None

        depth = 0

        for idx in range(start, len(text)):

            ch = text[idx]

            if ch == "{":

                depth += 1

            elif ch == "}":

                depth -= 1

                if depth == 0:

                    return text[start : idx + 1]

        return None

    @staticmethod
    def validate(text):

        blob = Validator.extract_json_object(text)

        if blob is None:

            error_log(
                (
                    "No JSON object extractable from model output "
                    "(not a thrown exception — no balanced { ... } "
                    "JSON object in reply)"
                ),
                None,
            )

            return "no_json_blob", False

        try:

            data = json.loads(blob)

            OutputSchema.model_validate(data)

            validate_log("JSON matches OutputSchema")

            return data, True

        except json.JSONDecodeError as exc:

            error_log("Structured JSON parse failed", exc, stack=False)

            return str(exc), False

        except ValidationError as exc:

            error_log("Structured JSON violates OutputSchema", exc, stack=False)

            return str(exc), False
