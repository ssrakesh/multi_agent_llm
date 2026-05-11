from llama_cpp import Llama
from logger import sys_log
import gc
import os

class LLM:

    def __init__(self, model_path):

        self.model_path = model_path

        sys_log(f"Loading model -> {model_path}")
        # Hide llama.cpp Noise
        os.environ["LLAMA_CPP_LOG_LEVEL"] = "0"
        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_gpu_layers=35,
            verbose=False
        )

    def generate(self, prompt):

        output = self.llm(
            prompt,
            max_tokens=128,
            temperature=0.7,
            top_p=0.9
        )

        return output["choices"][0]["text"]

    def unload(self):

        sys_log(f"Unloading model -> {self.model_path}")

        del self.llm

        gc.collect()
