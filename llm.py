import os
os.environ["LLAMA_CPP_LOG_LEVEL"] = "0"

from llama_cpp import Llama
from logger import sys_log
from config import *

class LLM:

    def __init__(self, model_path):

        self.model_path = model_path

        sys_log(f"Loading model -> {model_path}")

        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_gpu_layers=35,
            verbose=False
        )

    def generate(self, prompt):

        output = self.llm(
            prompt,
            max_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P
        )

        return output["choices"][0]["text"]

    def unload(self):

        sys_log(f"Unloading model -> {self.model_path}")

        del self.llm
