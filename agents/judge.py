import json
import re

from agents.validator import Validator

from logger import pipeline_log


_TECH_NEEDLES = (
    "hallucination",
    "quantization",
    "evidence",
    "throughput",
    "latency",
    "vram",
    "trade",
)


_PLACEHOLDER_MARKERS = (
    "your answer should include",
    "you must include",
    "you should write",
    "please provide only",
)


_HINT_STOPWORDS = frozenset(
    {
        "observation",
        "source",
        "corpus",
        "minute",
        "degrees",
        "temperature",
        "prefix",
        "merged",
        "passages",
        "embedder",
        "flat",
        "index",
        "lines",
        "style",
        "decode",
        "operator",
        "engineer",
    },
)


def _clip(txt, limit):

    if txt is None:

        return ""

    s = str(txt)

    if len(s) <= limit:

        return s

    return s[: limit - 20].rstrip() + (
        "\n…_(clipped for judge prompt context)_"
    )


def _hint_blob(observation_hints):

    if observation_hints is None:

        return ""

    if isinstance(
        observation_hints,
        str,
    ):

        return observation_hints.lower()

    try:

        return json.dumps(
            observation_hints,
            ensure_ascii=False,
        ).lower()

    except Exception:

        return str(observation_hints).lower()


def _hint_tokens(blob):

    if not blob.strip():

        return frozenset()

    return frozenset(
        m.group(0)
        for m in re.finditer(
            r"[a-z][a-z0-9_-]{4,}",
            blob,
        )
        if (
            m.group(0) not in _HINT_STOPWORDS
            and len(m.group(0)) <= 28
        )
    )


def _overlap_hits(answer, tokens):

    if not tokens:

        return 0

    a = answer.lower()

    return sum(
        1 for tok in tokens if tok in a
    )


def _looks_placeholder(txt):

    tl = txt.lower()

    return any(marker in tl for marker in _PLACEHOLDER_MARKERS)


def _technical_ground_score(text):

    raw = text.lower()
    tl = raw.replace("-", " ")

    s = sum(
        1 for n in _TECH_NEEDLES if n in tl.replace("_", " ")
    )

    if re.search(
        r"kv[- ]?\s*cache",
        raw,
    ):

        s += 2

    if re.search(
        r"\bfp16\b|\bint4\b|\bint8\b|\bquantiz",
        raw,
    ):

        s += 1

    if re.search(
        r"\b8\s*gb\b|\b8gb\b",
        raw,
    ):

        s += 1

    return s


def judge_try_llm(
    llm,
    query,
    planner_answer,
    executor_answer,
    *,
    observation_hints,
    combined_rag=False,
    combined_tool=False,
):

    from config import (
        JUDGE_LLM_PROMPT,        
        JUDGE_TEMPERATURE,
        MAX_JUDGE_NEW_TOKENS,
    )

    planner = str(planner_answer).strip()
    executor = str(executor_answer).strip()

    rag_note = (
        "yes — telemetry shows retrieval and/or external tool payloads "
        "were available to the agents."
        if (
            combined_rag
            or combined_tool
        )
        else (
            "both trajectories relied on plain generation only — "
            "judge specificity, correctness, and refusal patterns."
        )
    )

    prompt = JUDGE_LLM_PROMPT.format(
        query=_clip(query, 4000),
        planner=_clip(planner, 6000),
        executor=_clip(executor, 6000),
    )

    pipeline_log(
        "JUDGE",
        (
            "Model judge inference (respond with JSON choice only)."
        ),
    )

    raw = llm.generate(
        prompt,
        max_tokens=MAX_JUDGE_NEW_TOKENS,
        temperature=JUDGE_TEMPERATURE,
        repeat_penalty=1.2,   # Discourage repetition of the input
    )

    blob = Validator.extract_json_object(raw)

    if blob is None:

        pipeline_log(
            "JUDGE",
            "Model judge: no JSON object extracted — heuristic fallback.",
        )

        return None

    try:
        data = json.loads(blob)

    except json.JSONDecodeError:

        pipeline_log(
            "JUDGE",
            "Model judge: JSONDecodeError on decision blob — heuristic.",
        )

        return None

    choice = str(
        data.get(
            "choice",
            "",
        ),
    ).lower().strip()

    aliases_planner = frozenset(
        {
            "planner",
            "1",
            "a",
            "first",
            "trajectory_1",
            "traj_1",
        },
    )

    aliases_executor = frozenset(
        {
            "executor",
            "2",
            "b",
            "second",
            "trajectory_2",
            "traj_2",
        },
    )

    if choice in aliases_planner:

        pipeline_log(
            "JUDGE",
            f"Model judge selected **planner** (choice raw={choice!r}).",
        )

        return planner

    if choice in aliases_executor:

        pipeline_log(
            "JUDGE",
            f"Model judge selected **executor** (choice raw={choice!r}).",
        )

        return executor

    pipeline_log(
        "JUDGE",
        f"Model judge: unknown choice {choice!r} — heuristic fallback.",
    )

    return None


def judge_heuristic(
    planner,
    executor,
    *,
    observation_hints="",
    combined_rag=False,
    combined_tool=False,
):

    planner = str(planner).strip()
    executor = str(executor).strip()

    pipeline_log(
        "JUDGE",
        (
            "Heuristic judge: legacy triggers, tech keywords, "
            "corpus overlap, placeholder guard."
        ),
    )

    for idx, cand in enumerate(
        (planner, executor),
        start=1,
    ):

        tl = cand.lower()
        tl_compact = tl.replace("_", "").replace(" ", "")

        if (
            "online_api" in tl_compact
            or ("retrieval" in tl)
            or ("grounding" in tl)
        ):

            pipeline_log(
                "JUDGE",
                (
                    "Selected #%d via legacy lexical triggers "
                    "(tool/RAG narration)."
                    % idx
                ),
            )

            return cand

    sp = _technical_ground_score(planner)
    se = _technical_ground_score(executor)

    if max(
        sp,
        se,
    ) > 0 and (
        sp != se
    ):

        pick = executor if se > sp else planner

        pipeline_log(
            "JUDGE",
            (
                "Technical-topic score favors %s (%d vs %d)."
                % (
                    "[executor]"
                    if pick is executor
                    else "[planner]",
                    max(
                        sp,
                        se,
                    ),
                    min(
                        sp,
                        se,
                    ),
                )
            ),
        )

        return pick

    hb = _hint_blob(observation_hints)
    toks = _hint_tokens(hb)
    op = _overlap_hits(planner, toks)
    oe = _overlap_hits(executor, toks)

    if (
        combined_rag
        or combined_tool
    ) and toks and (
        oe != op
    ):

        pick = executor if oe > op else planner

        pipeline_log(
            "JUDGE",
            (
                "RAG hint overlap favors %s "
                "(planner=%d hits, executor=%d hits)."
                % (
                    "[executor]"
                    if pick is executor
                    else "[planner]",
                    op,
                    oe,
                )
            ),
        )

        return pick

    if _looks_placeholder(planner):

        pipeline_log(
            "JUDGE",
            (
                "Executor retained — planner matches meta-placeholder pattern "
                f"(executor_len={len(executor)})."
            ),
        )

        return executor if len(executor) > 50 else planner

    if (
        len(planner) < 160
        and len(executor)
        > max(
            300,
            max(
                1,
                len(planner),
            )
            * 2,
        )
    ):

        pipeline_log(
            "JUDGE",
            "Executor retained — planner answer much shorter/weaker.",
        )

        return executor

    if (
        len(executor) > len(planner) + 200
        and oe >= op
        and executor.count(" ") > planner.count(" ") + 12
    ):

        pipeline_log(
            "JUDGE",
            "Executor retained — longer + richer on tied heuristic scores.",
        )

        return executor

    pipeline_log(
        "JUDGE",
        "Fallback planner trajectory (#1).",
    )

    return planner


def judge_agent(
    query,
    answers,
    enabled=True,
    *,
    observation_hints="",
    combined_rag=False,
    combined_tool=False,
    llm=None,
):

    planner = str(answers[0]).strip()
    executor = str(answers[1]).strip()

    if not enabled:

        pipeline_log(
            "JUDGE",
            "Self-consistency disabled — planner trajectory.",
        )

        return planner

    from config import USE_LLM_JUDGE

    if llm is not None and USE_LLM_JUDGE:

        resolved = judge_try_llm(
            llm,
            query,
            planner,
            executor,
            observation_hints=observation_hints,
            combined_rag=combined_rag,
            combined_tool=combined_tool,
        )

        if resolved is not None:
            return resolved

        pipeline_log(
            "JUDGE",
            (
                "Falling back from model judge "
                "to deterministic heuristics."
            ),
        )

    return judge_heuristic(
        planner,
        executor,
        observation_hints=observation_hints,
        combined_rag=combined_rag,
        combined_tool=combined_tool,
    )
