import json
import time

from llm import LLM

from config import (
    AGENT_MODELS,
    BASELINE_PROMPT_TEMPLATE,
    EXECUTOR_PROMPT,
    MAX_BASELINE_NEW_TOKENS,
    MAX_JSON_REPAIR_ATTEMPTS,
    MAX_STRUCTURED_LLM_TOKENS,
    MAX_STRUCTURED_NATURAL_CHARS,
    PLANNER_PROMPT,
    STRUCTURED_JSON_PROMPT,
    STRUCTURED_REPEAT_PENALTY,
    STRUCTURED_TEMPERATURE,
    USE_LLM_JUDGE,
)

from logger import (
    section,
    proof_log,
    benchmark_log,
    pipeline_log,
)

from agents.planner import (
    run_react_agent,
)

from agents.judge import (
    judge_agent,
)

from agents.validator import (
    Validator,
)

from agents.repair import (
    RepairAgent,
)

from schema import (
    OutputSchema,
)


def _preview_query(query, limit=140):

    cleaned = query.replace("\n", " ").strip()

    if len(cleaned) > limit:

        return cleaned[: limit - 3] + "..."

    return cleaned


def _flatten_observations_for_judge(
    planner_observations,
    executor_observations,
):

    parts = []

    for seq in (
        planner_observations or [],
        executor_observations or [],
    ):

        for ob in seq:

            if isinstance(
                ob,
                dict,
            ):

                parts.append(
                    json.dumps(
                        ob,
                        ensure_ascii=False,
                    ),
                )

            else:

                parts.append(str(ob))

    return "\n".join(parts)


def _evaluation_case_label(meta, query):

    if not meta:

        return ""

    idx = meta.get("case_index")

    total = meta.get("case_total")

    if idx is None or total is None:

        return ""

    qprev = _preview_query(query, limit=100)

    cat = meta.get("category")

    if cat:

        return (
            f" (evaluation case {idx}/{total} — "
            f"{cat}: {qprev})"
        )

    return f" (evaluation case {idx}/{total} — {qprev})"


def _programmatic_package(query, natural_answer, used_tool, used_rag):

    payload = OutputSchema(
        query=query,
        answer=str(natural_answer),
        used_tool=bool(used_tool),
        used_rag=bool(used_rag),
    ).model_dump()

    return payload, json.dumps(payload, indent=2, ensure_ascii=False)


def _llm_structure_pass(
    model_path,
    query,
    natural_answer,
    used_tool,
    used_rag,
    apply_repairs,
):

    llm_local = LLM(model_path)

    prompt = STRUCTURED_JSON_PROMPT.format(
        query=query,
        natural_answer=(
            str(natural_answer)[:MAX_STRUCTURED_NATURAL_CHARS]
        ),
        used_tool=json.dumps(bool(used_tool)),
        used_rag=json.dumps(bool(used_rag)),
    )

    bundle = {
        "skipped": False,
        "repair_attempted": bool(apply_repairs),
    }

    current = llm_local.generate(
        prompt,
        max_tokens=MAX_STRUCTURED_LLM_TOKENS,
        temperature=STRUCTURED_TEMPERATURE,
        repeat_penalty=STRUCTURED_REPEAT_PENALTY,
    )

    bundle["raw_first"] = current

    data_first, ok_first = Validator.validate(current)

    bundle["valid_first_attempt"] = ok_first

    if ok_first:

        bundle["parsed_record"] = data_first

        bundle["valid_final"] = True

        bundle["repairs_used"] = 0

        llm_local.unload()

        return bundle

    repairs_used = 0

    if not apply_repairs:

        bundle["parsed_record"] = None

        bundle["valid_final"] = False

        bundle["repairs_used"] = 0

        llm_local.unload()

        return bundle

    fault = (
        data_first
        if isinstance(data_first, str)
        else "validation_failed"
    )

    attempts = MAX_JSON_REPAIR_ATTEMPTS

    while repairs_used < attempts:

        current = RepairAgent.repair(
            llm_local,
            current,
            fault,
            query=query,
            natural_answer=str(natural_answer),
            used_tool=used_tool,
            used_rag=used_rag,
        )

        repairs_used += 1

        probe, probe_ok = Validator.validate(current)

        if probe_ok:

            bundle["parsed_record"] = probe

            bundle["valid_final"] = True

            bundle["repairs_used"] = repairs_used

            bundle["raw_final"] = current

            llm_local.unload()

            return bundle

        fault = (
            probe if isinstance(probe, str) else str(probe)
        )

    bundle["parsed_record"] = None

    bundle["valid_final"] = False

    bundle["repairs_used"] = repairs_used

    bundle["raw_final"] = current

    llm_local.unload()

    return bundle

class MultiAgentPipeline:

    def __init__(self, tools, rag_system):

        self.tools = tools

        self.rag_system = rag_system

    def run_single_agent(self, query, meta=None):

        label = _evaluation_case_label(meta, query)

        section(
            f"SINGLE AGENT BASELINE{label}"
        )

        benchmark_log(f"Single-agent phase{label}")

        preview = _preview_query(query)

        pipeline_log(
            "BASELINE",
            f"Prompt preview: {preview!r}",
        )

        start = time.time()

        model = LLM(
            AGENT_MODELS["planner"]
        )

        answer = (
            model.generate(
                BASELINE_PROMPT_TEMPLATE.format(
                    query=query,
                ),
                max_tokens=MAX_BASELINE_NEW_TOKENS,
            )
        )

        if not str(answer).strip():

            benchmark_log(
                (
                    "Single-agent baseline returned empty completion — "
                    "keyword rubric will read 0%; tune "
                    "`BASELINE_PROMPT_TEMPLATE` / model choice if this persists."
                ),
            )

        model.unload()

        runtime = (
            time.time() - start
        )

        benchmark_log(
            f"Single-agent completed{label} — wall time {runtime:.2f}s",
        )

        prog_obj, prog_json = _programmatic_package(
            query,
            answer,
            False,
            False,
        )

        return {
            "answer": answer,
            "latency": runtime,
            "structured_programmatic": prog_obj,
            "structured_programmatic_json": prog_json,
        }

    def run_multi_agent(
        self,
        query,
        meta=None,
        benchmark_category=None,
        use_self_consistency=True,
        structured_llm_validation=False,
        structured_apply_repairs=True,
    ):

        label = _evaluation_case_label(meta, query)

        section(
            f"MULTI AGENT PIPELINE{label}",
        )

        preview = _preview_query(query)

        if label.strip():

            pipeline_log(
                "MULTI",
                f"Bench run — evaluating:{label.strip()}",
            )

        else:

            pipeline_log(
                "MULTI",
                f"Query preview for planner/executor: {preview!r}",
            )

        total_start = time.time()

        category = benchmark_category

        if meta and category is None:

            category = meta.get("category")

        benchmark_log(f"Planner ReAct kickoff{label} — model planner")

        planner = LLM(
            AGENT_MODELS["planner"],
        )

        planner_result = run_react_agent(
            planner,
            query,
            self.tools,
            self.rag_system,
            PLANNER_PROMPT,
            role="Planner",
            meta=meta,
            benchmark_category=category,
        )

        planner.unload()

        benchmark_log(f"Executor ReAct kickoff{label} — model executor")

        executor = LLM(
            AGENT_MODELS["executor"],
        )

        executor_result = run_react_agent(
            executor,
            query,
            self.tools,
            self.rag_system,
            EXECUTOR_PROMPT,
            role="Executor",
            meta=meta,
            benchmark_category=category,
        )

        executor.unload()

        pipeline_log(
            "JUDGE",
            (
                "Selecting planner vs executor final answer "
                f"(self-consistency={use_self_consistency}, "
                f"USE_LLM_JUDGE={USE_LLM_JUDGE})."
            ),
        )

        traj = [
            planner_result["answer"],
            executor_result["answer"],
        ]

        combined_tool = planner_result[
            "used_tool"
        ] or executor_result["used_tool"]

        combined_rag = planner_result[
            "used_rag"
        ] or executor_result["used_rag"]

        judge_hints = _flatten_observations_for_judge(
            planner_result["observations"],
            executor_result["observations"],
        )

        judge_model = None

        try:

            if (
                use_self_consistency
                and USE_LLM_JUDGE
            ):

                judge_model = LLM(
                    AGENT_MODELS[
                        "judge"
                    ],
                )

            final_answer = judge_agent(
                query,
                traj,
                enabled=use_self_consistency,
                observation_hints=judge_hints,
                combined_rag=combined_rag,
                combined_tool=combined_tool,
                llm=judge_model,
            )

        finally:

            if judge_model is not None:

                judge_model.unload()

        answer_no_judge = traj[0]

        structured_stats = {}

        base_pack, canonical_json_dump = (
            _programmatic_package(
                query,
                final_answer,
                combined_tool,
                combined_rag,
            )
        )

        structured_stats[
            "programmatic_safe_json"
        ] = base_pack

        if structured_llm_validation:

            pipeline_log(
                "STRUCTURED",
                (
                    "LLM JSON conformance pass "
                    f"(repairs={structured_apply_repairs})."
                ),
            )

            llm_bundle = (
                _llm_structure_pass(
                    AGENT_MODELS["structured"],
                    query,
                    final_answer,
                    combined_tool,
                    combined_rag,
                    structured_apply_repairs,
                )
            )

            structured_stats["llm"] = llm_bundle

            structured_stats[
                "llm_attempted_this_case"
            ] = True

        else:

            structured_stats["llm"] = {
                "skipped": True,
                "hint": (
                    "canonical JSON synthesized without extra LLM pass"
                ),
            }

            structured_stats[
                "llm_attempted_this_case"
            ] = False

        runtime = (
            time.time() - total_start
        )

        note = label.strip()

        elapsed_msg = "Multi-agent wall time end-to-end"

        if note:

            elapsed_msg += f" {note}"

        elapsed_msg += f": {runtime:.2f}s"

        benchmark_log(elapsed_msg)

        proof_log("Multi-agent orchestration completed.")

        return {
            "answer": final_answer,
            "answer_no_judge": answer_no_judge,
            "planner_answer": planner_result["answer"],
            "executor_answer": executor_result["answer"],
            "planner_used_tool": planner_result["used_tool"],
            "planner_used_rag": planner_result["used_rag"],
            "executor_used_tool": executor_result["used_tool"],
            "executor_used_rag": executor_result["used_rag"],
            "latency": runtime,
            "used_tool": combined_tool,
            "used_rag": combined_rag,
            "planner_observations": planner_result[
                "observations"
            ],
            "executor_observations": executor_result[
                "observations"
            ],
            "planner_react_trace": planner_result[
                "react_trace"
            ],
            "executor_react_trace": executor_result[
                "react_trace"
            ],
            "structured_pipeline": structured_stats,
            "canonical_structured_dump": canonical_json_dump,
        }
