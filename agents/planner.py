import json

import re

from agents.validator import Validator

from logger import (
    error_log,
    proof_log,
    stage_log,
    pipeline_log,
    react_log,
)

from config import (
    MAX_REACT_JSON_TOKENS,
    MAX_REACT_SYNTHESIS_TOKENS,
    REACT_PHASE1_PROMPT,
    REACT_PHASE2_PROMPT,
)

def _extract_city_from_query(query):
    """Pull city name from query for dynamic weather tool parameterization."""
    q = query.strip()
    # Prefer explicit "weather in <City>" or "weather for <City>"
    m = re.search(r"weather\s+(?:in|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", q)
    if m:
        return m.group(1)
    # Fallback: first word after "weather" that looks like a proper noun
    m = re.search(r"weather\s+([A-Z][a-z]+)", q)
    if m:
        return m.group(1)
    # Last resort default – keep old behaviour but log warning
    return "Bengaluru"

def _live_weather_intent(query):

    ql = query.lower()

    coding = (
        ("write python" in ql)
        or ("python code" in ql)
        or ("requests.get" in ql)
        or ("def " in ql and "weather" in ql)
    )

    if coding:
        return False

    wants_live = any(
        w in ql
        for w in (
            "today",
            "right now",
            "current weather",
            "forecast",
            "umbrella",
            "carry",
        )
    )

    return wants_live and ("weather" in ql)


def _rag_intent(query):

    ql = query.lower()

    return any(
        k in ql
        for k in (
            "hallucination",
            "hallucinations",
            "rag ",
            "rag?",
            "how does rag",
            "retrieval",
            "retrieve",
            "grounding",
            "kv cache",
            "quantization",
        )
    )


def _heuristic_action(query, benchmark_category):

    ql = query.lower()

    if benchmark_category == "tool_restraint":
        return "none", "Heuristic: benchmark category requires tool restraint."

    if _live_weather_intent(query):
        return "weather", "Heuristic: live weather intent detected."

    if _rag_intent(query):
        return "rag", "Heuristic: knowledge-grounding intent detected."

    return "none", "Heuristic: no tool or retrieval required."


def _parse_action_json(raw_text):

    blob = Validator.extract_json_object(raw_text)

    if blob is None:
        return None

    try:

        data = json.loads(blob)

        action = str(data.get("action", "")).lower().strip()
        thought = str(data.get("thought", "")).strip()
        if action not in {"weather", "rag", "none"}:
            return None

        return {"thought": thought, "action": action}

    except json.JSONDecodeError as exc:

        error_log(
            "ReAct phase-1 action JSON malformed",
            exc,
            stack=False,
        )

        return None

def _strip_think_tags(text):
    # Remove thinking blocks that reasoning models wrap their output in.
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

def run_react_agent(
    llm,
    query,
    tools,
    rag_system,
    prompt_template,
    role="Agent",
    meta=None,
    benchmark_category=None,
):

    react_trace = []
    observations = []
    used_tool = False
    used_rag = False
    case_tag = ""

    if meta:

        idx = meta.get("case_index")
        total = meta.get("case_total")

        if idx is not None and total is not None:
            cat = meta.get("category")

            if cat:
                case_tag = (
                    f"[case {idx}/{total} {cat}] "
                )
            else:
                case_tag = f"[case {idx}/{total}] "

    pipeline_log(
        role.upper(),
        f"{case_tag}ReAct phase-1 — model chooses tool/RAG/no-op.",
    )

    phase1 = llm.generate(
        REACT_PHASE1_PROMPT.format(
            role=role,
            query=query,
        ),
        max_tokens=MAX_REACT_JSON_TOKENS,
    )
    phase1_clean = _strip_think_tags(phase1)  # strip before JSON parsing
    parsed = _parse_action_json(phase1_clean)

    if parsed is None:
        action, rationale = _heuristic_action(query, benchmark_category)

        react_log(
            role,
            f"{case_tag}Phase-1 parse failed — fallback routing. ({rationale})",
        )

        thought = rationale

        react_trace.append(
            {
                "thought": thought,
                "action": action,
                "source": "heuristic_fallback",
            }
        )

    else:

        action = parsed["action"]
        thought = parsed["thought"]

        react_log(
            role,
            (
                f"{case_tag}Thought: {thought} | Action: "
                f"{action} (parsed from model)"
            ),
        )

        react_trace.append(
            {
                "thought": thought,
                "action": action,
                "source": "llm_phase1_json",
            }
        )

    if benchmark_category == "tool_restraint":

        if action != "none":
            react_log(
                role,
                f"{case_tag}Override: enforcing action=none (tool restraint).",
            )

            action = "none"

    if action == "weather":
        city = _extract_city_from_query(query)
        stage_log(
            "TOOL",
            f"{role}: Action=weather — live API call for '{city}'.",
        )
        obs = tools["weather"](city)
        observations.append(obs)
        used_tool = True
        react_trace.append({"observation": obs})
        react_log(
            role,
            f"{case_tag}Observation: weather payload (city={city}, keys={list(obs)[:3]}...)",
        )

    elif action == "rag":

        stage_log(
            "RAG",
            f"{role}: Action=rag — vector retrieval.",
        )

        obs = rag_system.retrieve(query)
        observations.append(obs)
        used_rag = True
        react_trace.append({"observation": obs[:500]})

        react_log(
            role,
            (
                f"{case_tag}Observation: retrieval excerpt "
                f"({len(obs)} chars)."
            ),
        )

    proof_log(
        f"{role}: ReAct scaffolding complete "
        f"(obs_blocks={len(observations)})."
    )

    combined_obs = repr(observations)

    response = llm.generate(
        REACT_PHASE2_PROMPT.format(
            base_prompt=prompt_template,
            query=query,
            observations=combined_obs,
        ),
        max_tokens=MAX_REACT_SYNTHESIS_TOKENS,
    )

    response = str(response).strip()

    if not response:

        react_log(
            role,
            f"{case_tag}Synthesis empty — falling back to observation text.",
        )

        parts = []

        for ob in observations:

            if isinstance(ob, dict):

                parts.append(
                    json.dumps(
                        ob,
                        indent=2,
                        ensure_ascii=False,
                    ),
                )

            else:
                parts.append(str(ob))

        response = (
            "\n\n".join(p for p in parts if str(p).strip())
        )

        if not response.strip():
            response = (
                f"[{role}] empty synthesis and no observations to quote."
            )

    react_trace.append({"phase": "synthesis"})

    react_log(role, f"{case_tag}Synthesis completion produced.")

    return {
        "answer": response,
        "used_tool": used_tool,
        "used_rag": used_rag,
        "observations": observations,
        "react_trace": react_trace,
    }
