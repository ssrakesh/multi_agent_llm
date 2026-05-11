import gc
import os
import torch

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig
)

from config import *

class LLM:

    def __init__(self, model_name):

        self.model_name = model_name
        model_folder = (f"models/{model_name.split('/')[-1]}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=model_folder,
        )

        quant_config = None

        if USE_4BIT:
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True
            )

        self.model = AutoModelForCausalLM.from_pretrained(            
            model_name,
            cache_dir=model_folder,
            device_map="auto",
            quantization_config=quant_config,
            torch_dtype=torch.float16
        )

    def generate(self, prompt, past_key_values=None):

        formatted_prompt = (
            f"<start_of_turn>user\n{prompt}<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )

        inputs = self.tokenizer(
            formatted_prompt,
            return_tensors="pt"
        ).to(self.model.device)

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            use_cache=True,
            return_dict_in_generate=True
        )

        text = self.tokenizer.decode(
            outputs.sequences[0],
            skip_special_tokens=True
        )

        return {
            "text": text,
            "past_key_values": outputs.past_key_values
        }

    def save_kv_cache(self, cache, cache_name):

        if not ENABLE_KV_CACHE_PERSISTENCE:
            return

        os.makedirs(KV_CACHE_DIR, exist_ok=True)

        path = f"{KV_CACHE_DIR}/{cache_name}.pt"

        torch.save(cache, path)

    def load_kv_cache(self, cache_name):

        path = f"{KV_CACHE_DIR}/{cache_name}.pt"

        if not os.path.exists(path):
            return None

        cache = torch.load(path)

        cache = tuple(
            tuple(t.to(self.model.device) for t in layer)
            for layer in cache
        )

        return cache

    def unload_model(self):

        del self.model

        torch.cuda.empty_cache()
        gc.collect()
