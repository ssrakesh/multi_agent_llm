import os

# Must be set before llama-cpp / ggml initializes (suppresses GGML chatter).
os.environ.setdefault("GGML_SILENT", "1")
os.environ.setdefault("LLAMA_CPP_LOG_LEVEL", "error")


from llama_cpp import Llama

from logger import error_log, llm_log, sys_log

from config import *


def _repair_error_extract(prompt):

    """Return verbatim validator/schema message between ERROR and BAD OUTPUT."""

    boundary = ("\nBAD OUTPUT:\n", "\nBAD OUTPUT:")

    head = ""

    cut = None

    for bk in boundary:

        cut = prompt.find(bk)

        if cut >= 0:

            head = prompt[:cut]

            break

    else:

        j = prompt.lower().find("\nbad output:")

        if j < 0:

            return None

        head = prompt[:j]

    _, needle, tail = head.partition("\nERROR:\n")

    if needle:

        return tail.strip() or "(empty ERROR block)"

    _, needle2, tail2 = head.partition("\nERROR:")

    if needle2:

        blob = tail2.lstrip(":").strip()

        return blob or "(empty ERROR block)"

    return None


class LLM:

    def __init__(self, model_path):

        self.model_path = model_path

        sys_log(f"Loading model -> {model_path}")

        try:

            self.llm = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_gpu_layers=35,
                verbose=False,
            )

        except Exception as exc:

            error_log(
                (
                    "Llama model load failed (bad path, GPU layers, "
                    "or incompatible llama-cpp build)"
                ),
                exc,
            )

            raise

    def generate(
        self,
        prompt,
        max_tokens=None,
        *,
        log_full_prompt=False,
        temperature=None,
        repeat_penalty=None,
    ):

        token_cap = (
            MAX_NEW_TOKENS
            if max_tokens is None
            else max_tokens
        )

        temp_use = TEMPERATURE if temperature is None else temperature

        infer_kw = dict(
            max_tokens=token_cap,
            temperature=temp_use,
            top_p=TOP_P,
        )

        if repeat_penalty is not None:

            infer_kw["repeat_penalty"] = repeat_penalty

        embedded_err = _repair_error_extract(prompt)

        if embedded_err is not None:

            llm_log(
                (
                    "[LLM] Structured-json repair ERROR (full, verbatim):\n"
                    f"{embedded_err}"
                ),
            )

        preview = prompt.replace("\n", " ").strip()
        if len(preview) > 120:
            preview = preview[:117] + "..."
        llm_log(f"Inference start (prompt ~{len(prompt)} chars, preview: {preview!r})")

        if log_full_prompt:

            llm_log(
                (
                    f"[LLM] Full prompt ({len(prompt)} chars):\n{prompt}"
                ),
            )

        try:

            output = self.llm(
                prompt,
                **infer_kw,
            )

            text = output["choices"][0]["text"]

        except Exception as exc:

            extra = ""

            if embedded_err is not None:

                extra = (
                    "\n--- Repair ERROR text (duplicate for crash context):\n"
                    f"{embedded_err}"
                )

            error_log(
                (
                    "Llama inference or response parsing failed"
                    + extra
                    + "\n--- Prompt snapshot (trunc 16k):\n"
                    + prompt[:16000]
                    + (
                        "\n...[prompt truncated]"
                        if len(prompt) > 16000
                        else ""
                    )
                ),
                exc,
                stack=True,
            )

            raise

        snippet = text.replace("\n", " ").strip()
        if len(snippet) > 100:
            snippet = snippet[:97] + "..."
        llm_log(f"Inference done (completion ~{len(text)} chars, preview: {snippet!r})")

        return text

    def unload(self):

        sys_log(f"Unloading model -> {self.model_path}")

        del self.llm
