import os

# Must be set before llama-cpp / ggml initializes (suppresses GGML chatter).
os.environ.setdefault("GGML_SILENT", "1")
os.environ.setdefault("LLAMA_CPP_LOG_LEVEL", "error")


from llama_cpp import Llama

from logger import error_log, llm_log, sys_log

from config import *


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

    def generate(self, prompt, max_tokens=None):

        token_cap = (
            MAX_NEW_TOKENS
            if max_tokens is None
            else max_tokens
        )

        preview = prompt.replace("\n", " ").strip()
        if len(preview) > 120:
            preview = preview[:117] + "..."
        llm_log(f"Inference start (prompt ~{len(prompt)} chars, preview: {preview!r})")

        try:

            output = self.llm(
                prompt,
                max_tokens=token_cap,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            )

            text = output["choices"][0]["text"]

        except Exception as exc:

            error_log("Llama inference or response parsing failed", exc)

            raise

        snippet = text.replace("\n", " ").strip()
        if len(snippet) > 100:
            snippet = snippet[:97] + "..."
        llm_log(f"Inference done (completion ~{len(text)} chars, preview: {snippet!r})")

        return text

    def unload(self):

        sys_log(f"Unloading model -> {self.model_path}")

        del self.llm
