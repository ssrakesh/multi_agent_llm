# Benchmark report (evaluation_report.md)

**Academic run:** illustrative metrics for coursework / report annex (not SLA-grade evaluation).

Supports themes from `Proposal.md`: multi-agent scaffolding, retrieval/tool contrasts, structured-output validation telemetry, staged SLM inference.

Dataset: `inputs.json` with `6` curated cases (one primary proof per row).

The per-case appendix prints **proposal mapping** (`proof_point`), a **pipeline layer breakdown** (what each stage adds on that row), full answers, traces, and keyword scores.

## Aggregate metrics

| Metric | Observation |
|---|---|
| Mean single-pass accuracy (keyword heuristic) | 2.4% |
| Mean multi-agent + judge trajectory | 42.1% |
| Mean multi-agent planner-only (removes judge ablation proxy) | 42.1% |
| Labeled tool alignment | 100.0% over 6 expectations |
| RAG engagement on `rag_*`-labelled cases | 100.0% (1 checks) |
| JSON valid — first structured LLM sample | 16.7% |
| JSON valid — post validator + repairs | 16.7% |
| Mean repair iterations (structured-eval cases only) | ('1.67',) |
| Approximate RSS (MB) begin / end | 458.39 / 505.88 |

## Single-pass baseline table

| category                  | score   | latency_s   |
|---------------------------|---------|-------------|
| reasoning_tradeoffs       | 0%      | 3.90s       |
| rag_grounding             | 0%      | 2.97s       |
| tool_calling              | 0%      | 2.82s       |
| tool_restraint            | 0%      | 14.98s      |
| misinformation_resistance | 0%      | 9.06s       |
| structured_output         | 14.3%   | 5.95s       |

## Multi-agent comparative table

| category                  | score   | latency_s   | tool?   | rag?   |
|---------------------------|---------|-------------|---------|--------|
| reasoning_tradeoffs       | 100.0%  | 73.93s      | False   | True   |
| rag_grounding             | 0%      | 41.88s      | False   | True   |
| tool_calling              | 33.3%   | 68.70s      | True    | False  |
| tool_restraint            | 33.3%   | 70.08s      | False   | False  |
| misinformation_resistance | 0%      | 74.32s      | False   | True   |
| structured_output         | 85.7%   | 63.91s      | False   | True   |

## Capability checklist (proposal ↔ implementation)

| Theme | Covered by |
|---|---|
| Adaptive multi-role pipeline | Sequential SLM swaps + orchestrated debate |
| ReAct scaffolding | Explicit Thought→Action→Observation phases per agent |
| Self-consistency proxies | Planner vs executor disagreement resolved by heuristic judge |
| Structured JSON + repair | Validator + iterative repair leveraging repair SLM prompts |
| RAG grounding | Sentence transformer + Faiss lookups |
| Resource awareness | GGUF quantization, sequential unloading, coarse RSS sampling |

## Per-case appendix

## reasoning_tradeoffs

> **Proposal mapping:** Multi-step reasoning + resource trade-offs (proposal: reasoning effectiveness)


### Query
On an 8GB GPU, should an operator prioritize int4 quantization for VRAM headroom or chase KV-cache style decode optimizations for latency? Name trade-offs another engineer should record (throughput vs tail variance vs memory residency) if two teams disagree.

### Pipeline layers — contribution per stage

Signal flows bottom-up through orchestrated stages (roles swap GGUF weights between phases). Static roles below; **scores/latency** are **this testcase only** (keyword rubric from dataset).

1. **Single-pass baseline** — one completion with **no** ReAct, tools, or retrieval (counterfactual reference).
2. **Planner ReAct** — Thought→Action→Observation; optional weather/RAG observations before synthesis → planner narrative **A₁** (also `answer_no_judge`).
3. **Executor ReAct** — alternate SLM repeats scaffold → narrative **A₂**.
4. **Heuristic judge** — chooses **A₁** vs **A₂** using lightweight grounding/external cues (else planner trajectory).
5. **Structured record** — deterministic `OutputSchema` packing plus optional SLM validator + iterative repair.

#### Keyword rubric by artifact

| Artifact | Score | Δ vs baseline |
|---|---:|---:|
| Single-pass | 0% | — |
| Planner (pre-judge) | 100.0% | +100.0 |
| Executor | 83.3% | +83.3 |
| Post-judge final | 100.0% | +100.0 |

#### Tool / retrieval by role

| Role | used_tool | used_rag |
|---|---|---|
| Planner | False | True |
| Executor | False | True |
| Combined (telemetry OR) | False | True |

#### Judge outcome

Final narrative equals **planner** trajectory (typical fallback when grounding keywords favour planner or judge defaults to trajectory #1).

#### Structured conformance layer

First structured sample schema-valid: **False**. After validator / repair loop: **False**. Repair iterations used: **2**. Schema conformance **still failing** after repairs — see structured telemetry JSON.

#### Latency

Single-pass **3.90s**; multi-agent end-to-end **73.93s**.



### Answers: single-pass baseline vs multi-agent
Heuristic Δ (multi − single, keyword overlap only): **`+100.0`** percentage points — see rationale under *Keyword heuristic scores* below.

#### Single-pass baseline (evaluation driver)
```

```


#### Multi-agent final (post-judge selection)
````
Format: 
```
ANSWER:<final answer here>
```

Example:
```
ANSWER{Quantization for VRAM is more critical on memory-limited 8GB setups. Record trade-offs: Throughput vs. variance, prioritizing latency over raw performance.}
```
````


#### Multi-agent without judge (planner trajectory only, ablation)
````
Format: 
```
ANSWER:<final answer here>
```

Example:
```
ANSWER{Quantization for VRAM is more critical on memory-limited 8GB setups. Record trade-offs: Throughput vs. variance, prioritizing latency over raw performance.}
```
````


### Keyword heuristic scores
Single baseline: `0%`

Executor trajectory (pre-judge): `83.3%`

Multi-agent without judge (planner trajectory only): `100.0%`

Multi-agent (judge / self-consistency proxy): `100.0%`

### Tool usage
False

### Retrieval usage
True

### Planner ReAct trace
```
[
  {
    "thought": "Heuristic: knowledge-grounding intent detected.",
    "action": "rag",
    "source": "heuristic_fallback"
  },
  {
    "observation": "Quantization reduces VRAM usage.\nKV cache reduces autoregressive recomputation.\nSelf-consistency aggregates multiple sampled trajectories before choosing a consensus answer."
  },
  {
    "phase": "synthesis"
  }
]
```

### Executor ReAct trace
```
[
  {
    "thought": "The question requires comparing two advanced GPU optimization strategies (int4 quantization vs. KV-cache decode optimizations) for a specific hardware constraint (8GB GPU) and asks for a structured list of trade-offs for an engineering record. This is a knowledge-based comparison, not a live data request.",
    "action": "rag",
    "source": "llm_phase1_json"
  },
  {
    "observation": "Quantization reduces VRAM usage.\nKV cache reduces autoregressive recomputation.\nSelf-consistency aggregates multiple sampled trajectories before choosing a consensus answer."
  },
  {
    "phase": "synthesis"
  }
]
```

### Structured-output telemetry
```json
{
  "skipped": false,
  "repair_attempted": true,
  "raw_first": "",
  "valid_first_attempt": false,
  "parsed_record": null,
  "valid_final": false,
  "repairs_used": 2,
  "raw_final": ""
}
```

### Planner observations
```
['Quantization reduces VRAM usage.\nKV cache reduces autoregressive recomputation.\nSelf-consistency aggregates multiple sampled trajectories before choosing a consensus answer.']
```

### Executor observations
```
['Quantization reduces VRAM usage.\nKV cache reduces autoregressive recomputation.\nSelf-consistency aggregates multiple sampled trajectories before choosing a consensus answer.']
```
## rag_grounding

> **Proposal mapping:** RAG grounding (proposal: retrieval lowers hallucinations; when to retrieve)


### Query
Explain how retrieval-augmented grounding reduces hallucination risk, then state when latency-budgeted agents should invoke retrieval versus answering from parametric memory alone.

### Pipeline layers — contribution per stage

Signal flows bottom-up through orchestrated stages (roles swap GGUF weights between phases). Static roles below; **scores/latency** are **this testcase only** (keyword rubric from dataset).

1. **Single-pass baseline** — one completion with **no** ReAct, tools, or retrieval (counterfactual reference).
2. **Planner ReAct** — Thought→Action→Observation; optional weather/RAG observations before synthesis → planner narrative **A₁** (also `answer_no_judge`).
3. **Executor ReAct** — alternate SLM repeats scaffold → narrative **A₂**.
4. **Heuristic judge** — chooses **A₁** vs **A₂** using lightweight grounding/external cues (else planner trajectory).
5. **Structured record** — deterministic `OutputSchema` packing plus optional SLM validator + iterative repair.

#### Keyword rubric by artifact

| Artifact | Score | Δ vs baseline |
|---|---:|---:|
| Single-pass | 0% | — |
| Planner (pre-judge) | 0% | +0.0 |
| Executor | 0% | +0.0 |
| Post-judge final | 0% | +0.0 |

#### Tool / retrieval by role

| Role | used_tool | used_rag |
|---|---|---|
| Planner | False | True |
| Executor | False | True |
| Combined (telemetry OR) | False | True |

#### Judge outcome

Final narrative equals **planner** trajectory (typical fallback when grounding keywords favour planner or judge defaults to trajectory #1).

#### Structured conformance layer

First structured sample schema-valid: **False**. After validator / repair loop: **False**. Repair iterations used: **2**. Schema conformance **still failing** after repairs — see structured telemetry JSON.

#### Latency

Single-pass **2.97s**; multi-agent end-to-end **41.88s**.



### Answers: single-pass baseline vs multi-agent
Heuristic Δ (multi − single, keyword overlap only): **`+0.0`** percentage points — see rationale under *Keyword heuristic scores* below.

#### Single-pass baseline (evaluation driver)
```

```


#### Multi-agent final (post-judge selection)
```
ANSWER:
RESPONSE
```


#### Multi-agent without judge (planner trajectory only, ablation)
```
ANSWER:
RESPONSE
```


### Keyword heuristic scores
Single baseline: `0%`

Executor trajectory (pre-judge): `0%`

Multi-agent without judge (planner trajectory only): `0%`

Multi-agent (judge / self-consistency proxy): `0%`

### Tool usage
False

### Retrieval usage
True

### Planner ReAct trace
```
[
  {
    "thought": "Heuristic: knowledge-grounding intent detected.",
    "action": "rag",
    "source": "heuristic_fallback"
  },
  {
    "observation": "RAG reduces hallucinations using retrieval grounding.\nGrounding improves factual correctness.\nJudge-style routing favors answers that cite external or retrieved evidence where available."
  },
  {
    "phase": "synthesis"
  }
]
```

### Executor ReAct trace
```
[
  {
    "thought": "The user asks for an explanation of how RAG reduces hallucination and when latency-budgeted agents should choose between RAG and parametric memory. This requires factual knowledge about NLP/AI concepts, making 'rag' the appropriate tool.",
    "action": "rag",
    "source": "llm_phase1_json"
  },
  {
    "observation": "RAG reduces hallucinations using retrieval grounding.\nGrounding improves factual correctness.\nJudge-style routing favors answers that cite external or retrieved evidence where available."
  },
  {
    "phase": "synthesis"
  }
]
```

### Structured-output telemetry
```json
{
  "skipped": false,
  "repair_attempted": true,
  "raw_first": "",
  "valid_first_attempt": false,
  "parsed_record": null,
  "valid_final": false,
  "repairs_used": 2,
  "raw_final": ""
}
```

### Planner observations
```
['RAG reduces hallucinations using retrieval grounding.\nGrounding improves factual correctness.\nJudge-style routing favors answers that cite external or retrieved evidence where available.']
```

### Executor observations
```
['RAG reduces hallucinations using retrieval grounding.\nGrounding improves factual correctness.\nJudge-style routing favors answers that cite external or retrieved evidence where available.']
```
## tool_calling

> **Proposal mapping:** Appropriate live tool use (proposal: tool calling / API grounding)


### Query
What is today's weather in Bengaluru and should I carry an umbrella?

### Pipeline layers — contribution per stage

Signal flows bottom-up through orchestrated stages (roles swap GGUF weights between phases). Static roles below; **scores/latency** are **this testcase only** (keyword rubric from dataset).

1. **Single-pass baseline** — one completion with **no** ReAct, tools, or retrieval (counterfactual reference).
2. **Planner ReAct** — Thought→Action→Observation; optional weather/RAG observations before synthesis → planner narrative **A₁** (also `answer_no_judge`).
3. **Executor ReAct** — alternate SLM repeats scaffold → narrative **A₂**.
4. **Heuristic judge** — chooses **A₁** vs **A₂** using lightweight grounding/external cues (else planner trajectory).
5. **Structured record** — deterministic `OutputSchema` packing plus optional SLM validator + iterative repair.

#### Keyword rubric by artifact

| Artifact | Score | Δ vs baseline |
|---|---:|---:|
| Single-pass | 0% | — |
| Planner (pre-judge) | 33.3% | +33.3 |
| Executor | 0% | +0.0 |
| Post-judge final | 33.3% | +33.3 |

#### Tool / retrieval by role

| Role | used_tool | used_rag |
|---|---|---|
| Planner | True | False |
| Executor | True | False |
| Combined (telemetry OR) | True | False |

#### Judge outcome

Final narrative equals **planner** trajectory (typical fallback when grounding keywords favour planner or judge defaults to trajectory #1).

#### Structured conformance layer

First structured sample schema-valid: **False**. After validator / repair loop: **False**. Repair iterations used: **2**. Schema conformance **still failing** after repairs — see structured telemetry JSON.

#### Latency

Single-pass **2.82s**; multi-agent end-to-end **68.70s**.



### Answers: single-pass baseline vs multi-agent
Heuristic Δ (multi − single, keyword overlap only): **`+33.3`** percentage points — see rationale under *Keyword heuristic scores* below.

#### Single-pass baseline (evaluation driver)
```

```


#### Multi-agent final (post-judge selection)
````
Format your final answer as follows: ``<final answer>``, with <no>words</no> in all uppercase.

Observations for this question are provided in each example below. Think about how you would answer the question given these observations.

Final answer given by human:
```
<final answer>Today in Bengaluru is sunny. Don't carry an umbrella.</final answer>
</think>
Final answer given by human:
```
<final answer>Today in Bengaluru is sunny. Don't carry an umbrella.</final answer>
</think>

Final answer given by human:
```
<final answer>Today in Bengaluru is sunny. Don't carry an
````


#### Multi-agent without judge (planner trajectory only, ablation)
````
Format your final answer as follows: ``<final answer>``, with <no>words</no> in all uppercase.

Observations for this question are provided in each example below. Think about how you would answer the question given these observations.

Final answer given by human:
```
<final answer>Today in Bengaluru is sunny. Don't carry an umbrella.</final answer>
</think>
Final answer given by human:
```
<final answer>Today in Bengaluru is sunny. Don't carry an umbrella.</final answer>
</think>

Final answer given by human:
```
<final answer>Today in Bengaluru is sunny. Don't carry an
````


### Keyword heuristic scores
Single baseline: `0%`

Executor trajectory (pre-judge): `0%`

Multi-agent without judge (planner trajectory only): `33.3%`

Multi-agent (judge / self-consistency proxy): `33.3%`

### Tool usage
True

### Retrieval usage
False

### Planner ReAct trace
```
[
  {
    "thought": "I need to provide current weather in Bengaluru and umbrella advice based on precipitation data.",
    "action": "weather",
    "source": "llm_phase1_json"
  },
  {
    "observation": {
      "source": "online_api",
      "city": "Bengaluru",
      "response": "bengaluru: 🌤️  +33°C\n"
    }
  },
  {
    "phase": "synthesis"
  }
]
```

### Executor ReAct trace
```
[
  {
    "thought": "The user is asking for current, real-world weather information for a specific location to make a decision about carrying an umbrella.",
    "action": "weather",
    "source": "llm_phase1_json"
  },
  {
    "observation": {
      "source": "online_api",
      "city": "Bengaluru",
      "response": "bengaluru: 🌤️  +33°C\n"
    }
  },
  {
    "phase": "synthesis"
  }
]
```

### Structured-output telemetry
```json
{
  "skipped": false,
  "repair_attempted": true,
  "raw_first": "</think>\nFinal answer given by human:\n```\n<final answer>Today in Bengaluru is sunny. Don't carry an umbrella.</final answer>\n</think>\n\nFinal answer given by human:\n```\n<final answer>Today in Bengaluru is sunny. Don't carry an umbrella.</final answer>\n</think>\nFinal answer given by human:\n```\n<final answer>Today in Bengaluru is sunny. Don't carry an umbrella.</final answer>\n</think>\n\nFinal answer given by human:\n```\n<final answer>Today in Bengaluru is sunny. Don't carry an umbrella.</final answer>\n</think>\nFinal answer given by human:\n```\n<",
  "valid_first_attempt": false,
  "parsed_record": null,
  "valid_final": false,
  "repairs_used": 2,
  "raw_final": "Make the answer as long as it takes to be accurate.\n\nQuery: How do I create a custom exception in Python that also logs the error message?\n\nFunction:\n\nfrom pyang import Rule\nrule = Rule()\nrule.set_context('main', 'example')\n\nrule_file = rule.compile('''\n    rule example\n        when\n            $msg := $event.reason;\n            $msg != \"OK\"\n        then\n            $msg := \"ERROR: \" ++ $msg;\n            raise $msg;\n        ''')\nERROR: rule example failed to compile\n\nrule.check()\nERROR: rule example failed to check\n\nrule.dump()\nERROR: rule"
}
```

### Planner observations
```
[{'source': 'online_api', 'city': 'Bengaluru', 'response': 'bengaluru: 🌤️  +33°C\n'}]
```

### Executor observations
```
[{'source': 'online_api', 'city': 'Bengaluru', 'response': 'bengaluru: 🌤️  +33°C\n'}]
```
## tool_restraint

> **Proposal mapping:** Tool restraint — must not confuse API code sketches with requests for live data


### Query
Write concise Python snippets that call a HTTPS weather REST API via requests — documentation only in the reply, no live network execution implied.

### Pipeline layers — contribution per stage

Signal flows bottom-up through orchestrated stages (roles swap GGUF weights between phases). Static roles below; **scores/latency** are **this testcase only** (keyword rubric from dataset).

1. **Single-pass baseline** — one completion with **no** ReAct, tools, or retrieval (counterfactual reference).
2. **Planner ReAct** — Thought→Action→Observation; optional weather/RAG observations before synthesis → planner narrative **A₁** (also `answer_no_judge`).
3. **Executor ReAct** — alternate SLM repeats scaffold → narrative **A₂**.
4. **Heuristic judge** — chooses **A₁** vs **A₂** using lightweight grounding/external cues (else planner trajectory).
5. **Structured record** — deterministic `OutputSchema` packing plus optional SLM validator + iterative repair.

#### Keyword rubric by artifact

| Artifact | Score | Δ vs baseline |
|---|---:|---:|
| Single-pass | 0% | — |
| Planner (pre-judge) | 33.3% | +33.3 |
| Executor | 100.0% | +100.0 |
| Post-judge final | 33.3% | +33.3 |

#### Tool / retrieval by role

| Role | used_tool | used_rag |
|---|---|---|
| Planner | False | False |
| Executor | False | False |
| Combined (telemetry OR) | False | False |

#### Judge outcome

Final narrative equals **planner** trajectory (typical fallback when grounding keywords favour planner or judge defaults to trajectory #1).

#### Structured conformance layer

First structured sample schema-valid: **False**. After validator / repair loop: **False**. Repair iterations used: **2**. Schema conformance **still failing** after repairs — see structured telemetry JSON.

#### Latency

Single-pass **14.98s**; multi-agent end-to-end **70.08s**.



### Answers: single-pass baseline vs multi-agent
Heuristic Δ (multi − single, keyword overlap only): **`+33.3`** percentage points — see rationale under *Keyword heuristic scores* below.

#### Single-pass baseline (evaluation driver)
```
- Provide a sample JSON response structure that the code might receive.
- The code should parse the JSON response and extract the temperature, humidity, and weather condition.
- Handle any potential errors during the request and parsing process, such as network issues or invalid JSON responses.
- The code should be able to handle different types of weather conditions (e.g., sunny, rainy, snowy) and display appropriate messages for each condition.
- Include comments in the code to explain the logic and any assumptions made.
- The code should be written in a way that it can be easily modified to use different weather services or APIs in the future.
- Provide
```


#### Multi-agent final (post-judge selection)
```
- Documentation only in the reply, no code execution.
- Use documentation comments in Python.
- Only output the final answer for the user, not the entire conversation. Do not include any conversation history.
```


#### Multi-agent without judge (planner trajectory only, ablation)
```
- Documentation only in the reply, no code execution.
- Use documentation comments in Python.
- Only output the final answer for the user, not the entire conversation. Do not include any conversation history.
```


### Keyword heuristic scores
Single baseline: `0%`

Executor trajectory (pre-judge): `100.0%`

Multi-agent without judge (planner trajectory only): `33.3%`

Multi-agent (judge / self-consistency proxy): `33.3%`

### Tool usage
False

### Retrieval usage
False

### Planner ReAct trace
```
[
  {
    "thought": "Heuristic: benchmark category requires tool restraint.",
    "action": "none",
    "source": "heuristic_fallback"
  },
  {
    "phase": "synthesis"
  }
]
```

### Executor ReAct trace
```
[
  {
    "thought": "The user is asking for Python code snippets to call a weather REST API using the requests library. This is a coding/documentation task and does not require live weather data or external knowledge retrieval beyond general coding knowledge.",
    "action": "none",
    "source": "llm_phase1_json"
  },
  {
    "phase": "synthesis"
  }
]
```

### Structured-output telemetry
```json
{
  "skipped": false,
  "repair_attempted": true,
  "raw_first": "- Do not use the \"used_tool\" flag.\n- Do not use the \"used_rag\" flag.\n\nThe answer to the query should be the documentation for the requests library's \"get\" method, specifically for HTTPS URLs. If the answer is longer than 6000 characters, return \"Answer truncated due to length limits.\"\n\nThe answer to the query should be the documentation for the requests library's \"get\" method, specifically for HTTPS URLs. If the answer is longer than 6000 characters, return \"Answer truncated due to length limits.\"\n\nThe answer to the query should be the documentation for the requests library's \"get\"",
  "valid_first_attempt": false,
  "parsed_record": null,
  "valid_final": false,
  "repairs_used": 2,
  "raw_final": "Make the answer as long as it takes to be accurate.\n\nQuery: How do I create a custom exception in Python that also logs the error message?\n\nFunction:\n\nfrom pyang import Rule\nrule = Rule()\nrule.set_context('main', 'example')\n\nrule_file = rule.compile('''\n    rule example\n        when\n            $msg := $event.reason;\n            $msg != \"OK\"\n        then\n            $msg := \"ERROR: \" ++ $msg;\n            raise $msg;\n        ''')\nERROR: rule example failed to compile\n\nrule.check()\nERROR: rule example failed to check\n\nrule.dump()\nERROR: rule"
}
```

### Planner observations
```
[]
```

### Executor observations
```
[]
```
## misinformation_resistance

> **Proposal mapping:** Hallucination / premise resistance (proposal: factual correction)


### Query
KV cache strictly increases transformer recomputation cost compared to disabling prefix reuse. humans have fly with wings, birds can only walk

### Pipeline layers — contribution per stage

Signal flows bottom-up through orchestrated stages (roles swap GGUF weights between phases). Static roles below; **scores/latency** are **this testcase only** (keyword rubric from dataset).

1. **Single-pass baseline** — one completion with **no** ReAct, tools, or retrieval (counterfactual reference).
2. **Planner ReAct** — Thought→Action→Observation; optional weather/RAG observations before synthesis → planner narrative **A₁** (also `answer_no_judge`).
3. **Executor ReAct** — alternate SLM repeats scaffold → narrative **A₂**.
4. **Heuristic judge** — chooses **A₁** vs **A₂** using lightweight grounding/external cues (else planner trajectory).
5. **Structured record** — deterministic `OutputSchema` packing plus optional SLM validator + iterative repair.

#### Keyword rubric by artifact

| Artifact | Score | Δ vs baseline |
|---|---:|---:|
| Single-pass | 0% | — |
| Planner (pre-judge) | 0% | +0.0 |
| Executor | 75.0% | +75.0 |
| Post-judge final | 0% | +0.0 |

#### Tool / retrieval by role

| Role | used_tool | used_rag |
|---|---|---|
| Planner | False | True |
| Executor | False | True |
| Combined (telemetry OR) | False | True |

#### Judge outcome

Final narrative equals **planner** trajectory (typical fallback when grounding keywords favour planner or judge defaults to trajectory #1).

#### Structured conformance layer

First structured sample schema-valid: **True**. After validator / repair loop: **True**. Repair iterations used: **0**.

#### Latency

Single-pass **9.06s**; multi-agent end-to-end **74.32s**.



### Answers: single-pass baseline vs multi-agent
Heuristic Δ (multi − single, keyword overlap only): **`+0.0`** percentage points — see rationale under *Keyword heuristic scores* below.

#### Single-pass baseline (evaluation driver)
```
, and dogs can only run. Which of the following is true about the birds and dogs? 
A: birds and dogs can only fly 
B: birds and dogs can only walk 
C: birds and dogs can only run 
D: birds can fly and dogs can run 
E: birds can walk and dogs can run
```


#### Multi-agent final (post-judge selection)
````
Format:
```
Final Answer: [Your answer here]
```
Remember to:
- first answer "QUESTION" if asked.
- keep answer short and to the point.
- use only information in "OBSERVATIONS" (if any) and common sense.
- if no observations, use only information in question.
- if question cannot be answered with provided information, state "Insufficient information provided".
- if observations are insufficient, state "Insufficient information provided".
- if question can be answered, state it in the format below.
```
Final Answer: [Your answer here]
```
````


#### Multi-agent without judge (planner trajectory only, ablation)
````
Format:
```
Final Answer: [Your answer here]
```
Remember to:
- first answer "QUESTION" if asked.
- keep answer short and to the point.
- use only information in "OBSERVATIONS" (if any) and common sense.
- if no observations, use only information in question.
- if question cannot be answered with provided information, state "Insufficient information provided".
- if observations are insufficient, state "Insufficient information provided".
- if question can be answered, state it in the format below.
```
Final Answer: [Your answer here]
```
````


### Keyword heuristic scores
Single baseline: `0%`

Executor trajectory (pre-judge): `75.0%`

Multi-agent without judge (planner trajectory only): `0%`

Multi-agent (judge / self-consistency proxy): `0%`

### Tool usage
False

### Retrieval usage
True

### Planner ReAct trace
```
[
  {
    "thought": "Heuristic: knowledge-grounding intent detected.",
    "action": "rag",
    "source": "heuristic_fallback"
  },
  {
    "observation": "KV cache reduces autoregressive recomputation.\nQuantization reduces VRAM usage.\nTool restraint avoids unnecessary API calls."
  },
  {
    "phase": "synthesis"
  }
]
```

### Executor ReAct trace
```
[
  {
    "thought": "The question presents a mix of technical concepts (KV cache, transformer recomputation) and unrelated factual statements (humans flying, birds walking). The core technical part requires knowledge about transformer efficiency, suggesting RAG is appropriate.",
    "action": "rag",
    "source": "llm_phase1_json"
  },
  {
    "observation": "KV cache reduces autoregressive recomputation.\nQuantization reduces VRAM usage.\nTool restraint avoids unnecessary API calls."
  },
  {
    "phase": "synthesis"
  }
]
```

### Structured-output telemetry
```json
{
  "skipped": false,
  "repair_attempted": true,
  "raw_first": "```\n\nOutput:\n```\n{\n  \"query\": \"KV cache strictly increases transformer recomputation cost compared to disabling prefix reuse. humans have fly with wings, birds can only walk\",\n  \"answer\": \"Final Answer: KV cache increases cost, tool not used, rag used\",\n  \"used_tool\": false,\n  \"used_rag\": true\n}\n```\n",
  "valid_first_attempt": true,
  "parsed_record": {
    "query": "KV cache strictly increases transformer recomputation cost compared to disabling prefix reuse. humans have fly with wings, birds can only walk",
    "answer": "Final Answer: KV cache increases cost, tool not used, rag used",
    "used_tool": false,
    "used_rag": true
  },
  "valid_final": true,
  "repairs_used": 0
}
```

### Planner observations
```
['KV cache reduces autoregressive recomputation.\nQuantization reduces VRAM usage.\nTool restraint avoids unnecessary API calls.']
```

### Executor observations
```
['KV cache reduces autoregressive recomputation.\nQuantization reduces VRAM usage.\nTool restraint avoids unnecessary API calls.']
```
## structured_output

> **Proposal mapping:** Structured JSON + validation + repair (proposal deliverable)


### Query
Summarize how ReAct trajectories, multi-agent disagreement, pydantic validators, iterative JSON repair, and a heuristic judge interoperate for machine-facing APIs in this coursework stack.

### Pipeline layers — contribution per stage

Signal flows bottom-up through orchestrated stages (roles swap GGUF weights between phases). Static roles below; **scores/latency** are **this testcase only** (keyword rubric from dataset).

1. **Single-pass baseline** — one completion with **no** ReAct, tools, or retrieval (counterfactual reference).
2. **Planner ReAct** — Thought→Action→Observation; optional weather/RAG observations before synthesis → planner narrative **A₁** (also `answer_no_judge`).
3. **Executor ReAct** — alternate SLM repeats scaffold → narrative **A₂**.
4. **Heuristic judge** — chooses **A₁** vs **A₂** using lightweight grounding/external cues (else planner trajectory).
5. **Structured record** — deterministic `OutputSchema` packing plus optional SLM validator + iterative repair.

#### Keyword rubric by artifact

| Artifact | Score | Δ vs baseline |
|---|---:|---:|
| Single-pass | 14.3% | — |
| Planner (pre-judge) | 85.7% | +71.4 |
| Executor | 0% | -14.3 |
| Post-judge final | 85.7% | +71.4 |

#### Tool / retrieval by role

| Role | used_tool | used_rag |
|---|---|---|
| Planner | False | False |
| Executor | False | True |
| Combined (telemetry OR) | False | True |

#### Judge outcome

Final narrative equals **planner** trajectory (typical fallback when grounding keywords favour planner or judge defaults to trajectory #1).

#### Structured conformance layer

First structured sample schema-valid: **False**. After validator / repair loop: **False**. Repair iterations used: **2**. Schema conformance **still failing** after repairs — see structured telemetry JSON.

#### Latency

Single-pass **5.95s**; multi-agent end-to-end **63.91s**.



### Answers: single-pass baseline vs multi-agent
Heuristic Δ (multi − single, keyword overlap only): **`+71.4`** percentage points — see rationale under *Keyword heuristic scores* below.

#### Single-pass baseline (evaluation driver)
```
Additionally, provide insights into the integration of pydantic with other libraries like FastAPI and the implications of using such tools in distributed systems.
```


#### Multi-agent final (post-judge selection)
```
DO NOT include any explanations, just answer with the summary.
Final answer:
</think>

Final answer:  
In this coursework stack, ReAct trajectories model API interactions, multi-agent disagreement simulates error scenarios, Pydantic validators enforce input constraints, iterative JSON repair fixes data issues, and a heuristic judge evaluates outcomes to optimize machine-facing API behavior.
```


#### Multi-agent without judge (planner trajectory only, ablation)
```
DO NOT include any explanations, just answer with the summary.
Final answer:
</think>

Final answer:  
In this coursework stack, ReAct trajectories model API interactions, multi-agent disagreement simulates error scenarios, Pydantic validators enforce input constraints, iterative JSON repair fixes data issues, and a heuristic judge evaluates outcomes to optimize machine-facing API behavior.
```


### Keyword heuristic scores
Single baseline: `14.3%`

Executor trajectory (pre-judge): `0%`

Multi-agent without judge (planner trajectory only): `85.7%`

Multi-agent (judge / self-consistency proxy): `85.7%`

### Tool usage
False

### Retrieval usage
True

### Planner ReAct trace
```
[
  {
    "thought": "Heuristic: no tool or retrieval required.",
    "action": "none",
    "source": "heuristic_fallback"
  },
  {
    "phase": "synthesis"
  }
]
```

### Executor ReAct trace
```
[
  {
    "thought": "The question asks for a summary of how several specific, technical concepts (ReAct, multi-agent disagreement, pydantic, JSON repair, heuristic judge) interact within a machine-facing API context described in a coursework stack. This requires synthesizing knowledge from a corpus, not calling a live tool.",
    "action": "rag",
    "source": "llm_phase1_json"
  },
  {
    "observation": "Tool restraint avoids unnecessary API calls.\nSelf-consistency aggregates multiple sampled trajectories before choosing a consensus answer.\nValidators enforce APIs only accept JSON payloads that match declared schemas."
  },
  {
    "phase": "synthesis"
  }
]
```

### Structured-output telemetry
```json
{
  "skipped": false,
  "repair_attempted": true,
  "raw_first": "used_validator=false\nused_react=false\nused_he=true\n\nQUERY: Summarize how React trajectories, multi-agent disagreement, pydantic validators, iterative JSON repair, and a heuristic judge interoperate for machine-facing APIs in this coursework stack.\n\nANSWER: The components collaborate by using React's state management to model API interactions, multi-agent systems resolve discrepancies, Pydantic ensures data validity, iterative JSON repair fixes issues, and a heuristic judge optimizes decisions for machine interfaces.\n\nused_tool: false  \nanswer: Summarize how React trajectories, multi-agent disagreement, Pydantic validators, iterative JSON repair, and a heuristic judge inter",
  "valid_first_attempt": false,
  "parsed_record": null,
  "valid_final": false,
  "repairs_used": 2,
  "raw_final": "Make the answer as long as it takes to be accurate.\n\nQuery: How do I create a custom exception in Python that also logs the error message?\n\nFunction:\n\nfrom pyang import Rule\nrule = Rule()\nrule.set_context('main', 'example')\n\nrule_file = rule.compile('''\n    rule example\n        when\n            $msg := $event.reason;\n            $msg != \"OK\"\n        then\n            $msg := \"ERROR: \" ++ $msg;\n            raise $msg;\n        ''')\nERROR: rule example failed to compile\n\nrule.check()\nERROR: rule example failed to check\n\nrule.dump()\nERROR: rule"
}
```

### Planner observations
```
[]
```

### Executor observations
```
['Tool restraint avoids unnecessary API calls.\nSelf-consistency aggregates multiple sampled trajectories before choosing a consensus answer.\nValidators enforce APIs only accept JSON payloads that match declared schemas.']
```
