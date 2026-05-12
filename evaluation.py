import json

from tabulate import tabulate

from config import (
    DEFAULT_STRUCTURED_LLM_EVAL,
    EVALUATION_REPORT_PATH,
    REPORTS_DIR,
)

from logger import (
    benchmark_log,
    error_log,
    eval_log,
)


_EXPECTED_USED_TOOL = {
    "tool_calling": True,
    "tool_restraint": False,
    "misinformation_resistance": False,
    "reasoning_tradeoffs": False,
    "rag_grounding": False,
    "structured_output": False,
}


def _rss_mb():

    try:

        import os

        import psutil

        return round(
            psutil.Process(
                os.getpid(),
            ).memory_info().rss
            / 1048578,
            2,
        )

    except Exception as exc:

        error_log(
            "RSS sampling skipped (psutil missing or unsupported)",
            exc,
        )

        return None


def _pct_mean(flags):

    if not flags:

        return None

    return round(
        100.0
        * sum(bool(x) for x in flags)
        / len(flags),
        1,
    )


def _eval_case_check_text(idx, total, category, query, limit=96):

    chunk = query.replace("\n", " ").strip()

    if len(chunk) > limit:

        chunk = chunk[: limit - 3] + "..."

    return f"case {idx}/{total} [{category}] — check: {chunk}"


def _snippet(traces):

    blob = json.dumps(
        traces,
        indent=2,
        ensure_ascii=False,
    )

    lines = blob.splitlines()

    if len(lines) > 24:

        keep = lines[:24]

        return "\n".join(keep) + "\n...(trace truncated)"

    return blob


def _fenced_answer(text, max_chars=12000):

    blob = str(text).strip()

    if len(blob) > max_chars:

        blob = blob[:max_chars].rstrip() + (
            "\n\n…_(answer truncated for report)_"
        )

    longest = 0

    idx = 0

    while idx < len(blob):

        if blob[idx] == "`":

            run = 0

            while idx + run < len(blob) and blob[idx + run] == "`":

                run += 1

            longest = max(longest, run)

            idx += run

            continue

        idx += 1

    fence_len = max(3, longest + 1)

    fence = "`" * fence_len

    return f"{fence}\n{blob}\n{fence}\n"


def _judge_trajectory_label(planner_a, executor_a, final_a):

    p = str(planner_a).strip()

    e = str(executor_a).strip()

    f = str(final_a).strip()

    if p == e == f:

        return (
            "Planner and executor narratives matched — judge tie-break unused "
            "(same text)."
        )

    if f == e and f != p:

        return (
            "Final narrative equals **executor** trajectory "
            "(judge favoured grounding cue or executor wording)."
        )

    if f == p:

        return (
            "Final narrative equals **planner** trajectory "
            "(typical fallback when grounding keywords favour planner "
            "or judge defaults to trajectory #1)."
        )

    return (
        "Final narrative differs from both stored trajectories "
        "(whitespace/normalisation — inspect answers section)."
    )


def _structured_layer_summary(structured_flag, ll_bundle):

    if not structured_flag:

        return (
            "Structured SLM conformance **disabled for this row** "
            "(dataset `structured_eval` / global default). Programmatic "
            "`OutputSchema` JSON is still emitted from telemetry."
        )

    if not isinstance(ll_bundle, dict):

        return "Structured telemetry unavailable."

    if ll_bundle.get("skipped"):

        return (
            "Structured SLM stage **skipped** — canonical JSON produced "
            "only via `_programmatic_package` from final narrative + flags."
        )

    v1 = ll_bundle.get("valid_first_attempt")

    vf = ll_bundle.get("valid_final")

    rep = ll_bundle.get("repairs_used", 0)

    parts = [
        f"First structured sample schema-valid: **{v1}**.",
        f"After validator / repair loop: **{vf}**.",
        f"Repair iterations used: **{rep}**.",
    ]

    if v1 is False and vf is True:

        parts.append(
            "**Repair layer** recovered conformant JSON from invalid "
            "first-pass model output."
        )

    elif vf is False:

        parts.append(
            "Schema conformance **still failing** after repairs — "
            "see structured telemetry JSON."
        )

    return " ".join(parts)


PIPELINE_LAYERS_CONCEPT_MD = """## Pipeline layers — contribution per stage

How information moves through the stack (**once for the whole report**; each testcase below only adds tables and timings).

1. **Single-pass baseline** — one completion with no ReAct phases, tools, or retrieval (reference latency + keyword rubric).
2. **Planner ReAct** — Thought→Action→Observation; optional weather/RAG observations → planner narrative **A₁** (`answer_no_judge`).
3. **Executor ReAct** — alternate SLM repeats the scaffold → **A₂**.
4. **Heuristic judge** — picks **A₁** vs **A₂** using grounding keywords (else planner trajectory).
5. **Structured record** — deterministic `OutputSchema` packing; optional structured SLM validate/repair.

"""


def _pipeline_case_metrics_md(
    *,
    s_score,
    p_only,
    e_score,
    m_score,
    baseline_latency,
    multi_latency,
    judge_label,
    planner_tool,
    planner_rag,
    exec_tool,
    exec_rag,
    combined_tool,
    combined_rag,
    structured_flag,
    ll_bundle,
):

    dp = round(p_only - s_score, 1)

    de = round(e_score - s_score, 1)

    dm = round(m_score - s_score, 1)

    struct_txt = _structured_layer_summary(
        structured_flag,
        ll_bundle,
    )

    return (
        "### Layer metrics (this testcase)\n\n"
        "#### Keyword rubric by artifact\n\n"
        "| Artifact | Score | Δ vs baseline |\n"
        "|---|---:|---:|\n"
        f"| Single-pass | {s_score}% | — |\n"
        f"| Planner (pre-judge) | {p_only}% | {dp:+.1f} |\n"
        f"| Executor | {e_score}% | {de:+.1f} |\n"
        f"| Post-judge final | {m_score}% | {dm:+.1f} |\n\n"
        "#### Tool / retrieval by role\n\n"
        "| Role | used_tool | used_rag |\n"
        "|---|---|---|\n"
        f"| Planner | {planner_tool} | {planner_rag} |\n"
        f"| Executor | {exec_tool} | {exec_rag} |\n"
        f"| Combined (telemetry OR) | {combined_tool} | {combined_rag} |\n\n"
        "#### Judge outcome\n\n"
        f"{judge_label}\n\n"
        "#### Structured conformance layer\n\n"
        f"{struct_txt}\n\n"
        "#### Latency\n\n"
        f"Single-pass **{baseline_latency}s**; multi-agent end-to-end "
        f"**{multi_latency}s**.\n\n"
    )


class Evaluator:

    def __init__(self, pipeline):

        self.pipeline = pipeline

    def score(self, answer, positive, negative):

        txt = str(answer).lower()

        pos = 0

        neg = 0

        for p in positive:

            if p.lower() in txt:

                pos += 1

        for n in negative:

            if n.lower() in txt:

                neg += 1

        pos_score = (
            pos / len(positive)
        ) * 100

        neg_penalty = (
            neg / max(1, len(negative))
        ) * 100

        return max(
            0,
            round(pos_score - neg_penalty, 1),
        )

    def evaluate(self, dataset_path):

        rss_open = _rss_mb()

        if rss_open is not None:

            benchmark_log(
                (
                    "Process RSS (approx.) at evaluation start "
                    f"{rss_open} MB"
                ),
            )

        try:

            with open(dataset_path, encoding="utf-8") as fh:

                dataset = json.load(fh)

        except (OSError, json.JSONDecodeError) as exc:

            error_log(
                (
                    "Benchmark dataset unreadable or invalid JSON — "
                    f"{dataset_path!r}"
                ),
                exc,
                stack=True,
            )

            raise

        n_cases = len(dataset)

        benchmark_log(
            (
                "Starting benchmark driver — "
                f"{n_cases} cases from "
                f"{dataset_path}"
            ),
        )

        single_rows = []

        multi_rows = []

        planner_only_scores = []

        json_first_pass = []

        json_after_repair = []

        structured_repairs = []

        tool_hits = 0

        tool_checked = 0

        rag_hits = 0

        rag_checked = 0

        md_sections = []

        sum_single = 0.0

        sum_multi = 0.0

        for idx, task in enumerate(dataset, start=1):

            category = task["category"]

            query = task["query"]

            positives = task["positive_keywords"]

            negatives = task["negative_keywords"]

            proof_line = ""

            proof_point = task.get("proof_point")

            if proof_point:

                proof_line = (
                    "\n> **Proposal mapping:** "
                    f"{proof_point}\n\n"
                )

            structured_flag = task.get(
                "structured_eval",
                DEFAULT_STRUCTURED_LLM_EVAL,
            )

            meta = {
                "case_index": idx,
                "case_total": n_cases,
                "category": category,
            }

            check_line = (
                _eval_case_check_text(
                    idx,
                    n_cases,
                    category,
                    query,
                )
            )

            eval_log(
                (
                    f"{check_line} — "
                    f"structured_llm={structured_flag}"
                ),
            )

            eval_log(
                (
                    "Stage single-agent baseline — "
                    f"{check_line}"
                ),
            )

            baseline = (
                self.pipeline.run_single_agent(
                    query,
                    meta=meta,
                )
            )

            eval_log(
                (
                    "Stage multi-agent (debate+judge+json) — "
                    f"{check_line}"
                ),
            )

            full = (
                self.pipeline.run_multi_agent(
                    query,
                    meta=meta,
                    benchmark_category=category,
                    use_self_consistency=True,
                    structured_llm_validation=structured_flag,
                    structured_apply_repairs=True,
                )
            )

            ll_bundle = (
                full["structured_pipeline"]["llm"]
            )

            s_score = self.score(
                baseline["answer"],
                positives,
                negatives,
            )

            m_score = self.score(
                full["answer"],
                positives,
                negatives,
            )

            p_only = self.score(
                full["answer_no_judge"],
                positives,
                negatives,
            )

            e_score = self.score(
                full["executor_answer"],
                positives,
                negatives,
            )

            judge_label = _judge_trajectory_label(
                full["planner_answer"],
                full["executor_answer"],
                full["answer"],
            )

            layers_md = _pipeline_case_metrics_md(
                s_score=s_score,
                p_only=p_only,
                e_score=e_score,
                m_score=m_score,
                baseline_latency=f"{baseline['latency']:.2f}",
                multi_latency=f"{full['latency']:.2f}",
                judge_label=judge_label,
                planner_tool=full["planner_used_tool"],
                planner_rag=full["planner_used_rag"],
                exec_tool=full["executor_used_tool"],
                exec_rag=full["executor_used_rag"],
                combined_tool=full["used_tool"],
                combined_rag=full["used_rag"],
                structured_flag=structured_flag,
                ll_bundle=ll_bundle,
            )

            sum_single += s_score

            sum_multi += m_score

            benchmark_log(
                (
                    f"{check_line} — "
                    f"keyword score single="
                    f"{s_score}% multi="
                    f"{m_score}% "
                    f"multi(no judge)="
                    f"{p_only}% | "
                    f"latency single="
                    f"{baseline['latency']:.2f}s "
                    f"multi={full['latency']:.2f}s"
                ),
            )

            planner_only_scores.append(p_only)

            expectation = _EXPECTED_USED_TOOL.get(
                category,
            )

            if expectation is not None:

                tool_checked += 1

                if full["used_tool"] == expectation:

                    tool_hits += 1

            if str(category).startswith("rag_"):

                rag_checked += 1

                if full["used_rag"]:

                    rag_hits += 1

            if (
                structured_flag
                and isinstance(ll_bundle, dict)
                and not ll_bundle.get("skipped")
            ):

                json_first_pass.append(
                    ll_bundle.get(
                        "valid_first_attempt",
                    ),
                )

                json_after_repair.append(
                    ll_bundle.get(
                        "valid_final",
                    ),
                )

                structured_repairs.append(
                    ll_bundle.get(
                        "repairs_used",
                        0,
                    ),
                )

            single_rows.append(
                [
                    category,
                    f"{s_score}%",
                    f"{baseline['latency']:.2f}s",
                ],
            )

            multi_rows.append(
                [
                    category,
                    f"{m_score}%",
                    f"{full['latency']:.2f}s",
                    full["used_tool"],
                    full["used_rag"],
                ],
            )

            ll_json = "{}"

            if structured_flag:

                ll_json = json.dumps(
                    ll_bundle,
                    indent=2,
                    ensure_ascii=False,
                )

            delta_kw = round(
                m_score - s_score,
                1,
            )

            md_sections.append(
                f"""## {category}
{proof_line}
### Query
{query}

{layers_md}

### Answers: single-pass baseline vs multi-agent
Heuristic Δ (multi − single, keyword overlap only): **`{delta_kw:+.1f}`** percentage points — see rationale under *Keyword heuristic scores* below.

#### Single-pass baseline (evaluation driver)
{_fenced_answer(baseline["answer"])}

#### Multi-agent final (post-judge selection)
{_fenced_answer(full["answer"])}

#### Multi-agent without judge (planner trajectory only, ablation)
{_fenced_answer(full["answer_no_judge"])}

### Keyword heuristic scores
Single baseline: `{s_score}%`

Executor trajectory (pre-judge): `{e_score}%`

Multi-agent without judge (planner trajectory only): `{p_only}%`

Multi-agent (judge / self-consistency proxy): `{m_score}%`

### Tool usage
{full["used_tool"]}

### Retrieval usage
{full["used_rag"]}

### Planner ReAct trace
```
{_snippet(full["planner_react_trace"])}
```

### Executor ReAct trace
```
{_snippet(full["executor_react_trace"])}
```

### Structured-output telemetry
```json
{ll_json}
```

### Planner observations
```
{full["planner_observations"]}
```

### Executor observations
```
{full["executor_observations"]}
```
"""
            )

        tool_rate = ""

        if tool_checked:

            tool_rate = "%.1f" % (
                100.0 * tool_hits / tool_checked,
            )

        else:

            tool_rate = "n/a"

        rag_rate = ""

        if rag_checked:

            rag_rate = "%.1f" % (
                100.0 * rag_hits / rag_checked,
            )

        else:

            rag_rate = "n/a"

        first_json = (
            "%.1f" % _pct_mean(json_first_pass)
            if json_first_pass
            else "n/a"
        )

        repaired_json = (
            "%.1f" % _pct_mean(json_after_repair)
            if json_after_repair
            else "n/a"
        )

        if structured_repairs:

            repair_avg = (
                "%.2f"
                % (
                    sum(structured_repairs)
                    / len(structured_repairs),
                ),
            )

        else:

            repair_avg = "0"

        avg_single = sum_single / n_cases

        avg_multi = sum_multi / n_cases

        avg_planner_only = sum(
            planner_only_scores,
        ) / max(1, n_cases)

        rss_close = _rss_mb()

        if rss_close is not None:

            drift = ""

            if rss_open is not None:

                drift = "%.2f" % (
                    rss_close - rss_open,
                )

                benchmark_log(
                    (
                        f"RSS end {rss_close} MB "
                        f"(delta versus start {drift} MB)"
                    ),
                )

        report_intro = (
            f"""# Benchmark report ({EVALUATION_REPORT_PATH.name})

**Academic run:** illustrative metrics for coursework / report annex (not SLA-grade evaluation).

Supports themes from `Proposal.md`: multi-agent scaffolding, retrieval/tool contrasts, structured-output validation telemetry, staged SLM inference.

Dataset: `{dataset_path}` with `{n_cases}` curated cases (one primary proof per row).

The per-case appendix lists **proposal mapping** (`proof_point`), **layer metrics** (scores, routing, judge, structured telemetry, timings—methodology explained once below), answers, traces, and keyword lines.

"""
        )

        metrics_block = f"""## Aggregate metrics

| Metric | Observation |
|---|---|
| Mean single-pass accuracy (keyword heuristic) | {avg_single:.1f}% |
| Mean multi-agent + judge trajectory | {avg_multi:.1f}% |
| Mean multi-agent planner-only (removes judge ablation proxy) | {avg_planner_only:.1f}% |
| Labeled tool alignment | {tool_rate}% over {tool_checked} expectations |
| RAG engagement on `rag_*`-labelled cases | {rag_rate}% ({rag_checked} checks) |
| JSON valid — first structured LLM sample | {first_json}% |
| JSON valid — post validator + repairs | {repaired_json}% |
| Mean repair iterations (structured-eval cases only) | {repair_avg} |
| Approximate RSS (MB) begin / end | {rss_open if rss_open is not None else "n/a"} / {rss_close if rss_close is not None else "n/a"} |

"""

        tbl_single = "## Single-pass baseline table\n\n" + tabulate(
            single_rows,
            headers=[
                "category",
                "score",
                "latency_s",
            ],
            tablefmt="github",
        )

        tbl_multi = "\n\n## Multi-agent comparative table\n\n" + tabulate(
            multi_rows,
            headers=[
                "category",
                "score",
                "latency_s",
                "tool?",
                "rag?",
            ],
            tablefmt="github",
        )

        mapping_md = """

## Capability checklist (proposal ↔ implementation)

| Theme | Covered by |
|---|---|
| Adaptive multi-role pipeline | Sequential SLM swaps + orchestrated debate |
| ReAct scaffolding | Explicit Thought→Action→Observation phases per agent |
| Self-consistency proxies | Planner vs executor disagreement resolved by heuristic judge |
| Structured JSON + repair | Validator + iterative repair leveraging repair SLM prompts |
| RAG grounding | Sentence transformer + Faiss lookups |
| Resource awareness | GGUF quantization, sequential unloading, coarse RSS sampling |

"""

        appendix = (
            PIPELINE_LAYERS_CONCEPT_MD
            + "\n## Per-case appendix\n\n"
            + "".join(md_sections)
        )

        full_report = (
            report_intro
            + metrics_block
            + tbl_single
            + tbl_multi
            + mapping_md
            + appendix
        )

        REPORTS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:

            EVALUATION_REPORT_PATH.write_text(
                full_report,
                encoding="utf-8",
            )

        except OSError as exc:

            error_log(
                (
                    "Failed writing evaluation report — "
                    f"{EVALUATION_REPORT_PATH!r}"
                ),
                exc,
            )

            raise

        benchmark_log(
            (
                "Markdown dossier flushed to "
                f"{EVALUATION_REPORT_PATH}"
            ),
        )

        print("\nSINGLE PASS TABLE\n")

        print(
            tabulate(
                single_rows,
                headers=[
                    "category",
                    "score",
                    "latency_s",
                ],
                tablefmt="github",
            ),
        )

        print("\nMULTI AGENT TABLE\n")

        print(
            tabulate(
                multi_rows,
                headers=[
                    "category",
                    "score",
                    "latency_s",
                    "tool?",
                    "rag?",
                ],
                tablefmt="github",
            ),
        )

        return EVALUATION_REPORT_PATH
