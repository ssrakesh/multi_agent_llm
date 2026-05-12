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
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(text):
            # Find next opening brace
            brace_pos = text.find("{", idx)
            if brace_pos == -1:
                return None
            try:
                obj, end = decoder.raw_decode(text, brace_pos)
                # We only accept dict objects, not lists/strings/numbers
                if isinstance(obj, dict):
                    return text[brace_pos:end]
                # If it parsed something else, move past it
                idx = end
            except json.JSONDecodeError:
                # Could be incomplete or malformed; move past this brace
                idx = brace_pos + 1
        return None
        if not isinstance(text, str):
            text = str(text)
        # Find first '{'
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
                if depth < 0:          # stray closing brace before we even opened one
                    # we can try to recover later, but let's just abort this attempt
                    return None
                if depth == 0:
                    candidate = text[start : idx + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        # not a valid JSON object – keep looking?
                        # but we already hit balanced braces; it's broken
                        return None
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
