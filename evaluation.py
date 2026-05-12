import json
import re

from tabulate import tabulate

from config import (
    DEFAULT_STRUCTURED_LLM_EVAL,
    EVALUATION_REPORT_PATH,
    EVAL_REPORT_BODY_CHAR_CAP,
    EVAL_REPORT_REACT_TRACE_LINES,
    REPORTS_DIR,
)

from logger import (
    benchmark_log,
    error_log,
    eval_log,
    rubric_log,
)


_EXPECTED_USED_TOOL = {
    "tool_calling": True,
    "tool_restraint": False,
    "misinformation_resistance": False,
    "reasoning_tradeoffs": False,
    "rag_grounding": False,
    "structured_output": False,
}


def _rubric_normalize(blob):

    """Match surface for substring rubric — reduces false zeros from formatting.

    Underscores in keywords (e.g. ``online_api``) align with spaced prose;
    ``8 gb`` / ``8GB`` align with ``8gb``-style checklist phrases.
    """

    t = str(blob).lower().replace("_", " ")

    t = re.sub(
        r"\s+",
        " ",
        t,
    ).strip()

    t = re.sub(
        r"(\d)\s*gb\b",
        r"\1gb",
        t,
    )

    return t


def _rubric_breakdown(answer, positive, negative):

    blob = str(answer)

    txt = _rubric_normalize(blob)

    matched_pos = [
        p
        for p in positive
        if _rubric_normalize(p) in txt
    ]

    matched_neg = [
        n
        for n in negative
        if _rubric_normalize(n) in txt
    ]

    if positive:

        pos_score = (
            len(matched_pos)
            / len(positive)
        ) * 100

    else:

        pos_score = 0.0

    neg_penalty = (
        len(matched_neg)
        / max(1, len(negative))
    ) * 100

    missed_pos = [
        p
        for p in positive
        if _rubric_normalize(p) not in txt
    ]

    final_score = max(
        0,
        round(pos_score - neg_penalty, 1),
    )

    return (
        final_score,
        matched_pos,
        matched_neg,
        missed_pos,
        len(blob),
        pos_score,
        neg_penalty,
    )


def _rubric_diagnostics_md(tracks):

    def fmt(xs):

        return ", ".join(xs) if xs else "(none)"

    rows = "".join(
        (
            (
                f"| {label} | {score}% | "
                f"{pw:.1f}% | {nw:.1f}% | "
                f"{nch} | "
                f"{fmt(mp)} | {fmt(mn)} | {fmt(missed)} |\n"
            )
        )
        for (
            label,
            score,
            nch,
            mp,
            mn,
            missed,
            pw,
            nw,
        ) in tracks
    )

    return (
        "### Keyword lists (substring evidence)\n\n"
        "**Rubric inputs for this row:** counts use normalized substring "
        "match (`_`, spacing, `8 gb` vs `8gb`) — see "
        "`evaluation._rubric_normalize`. Dataset phrases are unchanged in "
        "the appendix columns. **+weight** = `100 × (+hits / N₊)`; "
        "**−penalty** = `100 × (−hits / max(1, N₋))`. "
        "**Net** = `max(0, round(+weight − −penalty, 1))` (same as evaluation code).\n\n"
        "| Track | Net | +weight | −penalty | Chars | + matched text | − matched text | + missed |\n"
        "|---|---:|---:|---:|---:|---|---|---|\n"
        f"{rows}\n"
    )


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

    cap = EVAL_REPORT_REACT_TRACE_LINES

    if cap is None:

        return blob

    lines = blob.splitlines()

    if len(lines) <= cap:

        return blob

    keep = lines[:cap]

    return (
        "\n".join(keep)
        + "\n...(trace truncated — set `EVAL_REPORT_REACT_TRACE_LINES=None` "
        "in `config.py` for full JSON)_"
    )


def _fenced_answer(text, max_chars=None):

    blob = str(text).strip()

    effective = (
        EVAL_REPORT_BODY_CHAR_CAP
        if max_chars is None
        else max_chars
    )

    if effective is not None and len(blob) > effective:

        blob = blob[:effective].rstrip() + (
            "\n\n…_(truncated — set `EVAL_REPORT_BODY_CHAR_CAP=None` "
            "in `config.py` for full text)_"
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


_RAG_REPORT_META = {
    "corpus_file": "data/knowledge_base.txt",
    "embedder_model": "all-MiniLM-L6-v2",
    "index_backend": "faiss.IndexFlatL2",
    "top_k": 3,
}


def _observations_payload_md(
    observations,
    *,
    max_chars=None,
    used_tool=False,
    used_rag=False,
):

    """Pretty-print observation list passed into ReAct phase-2 (tool / RAG)."""

    cap = (
        EVAL_REPORT_BODY_CHAR_CAP
        if max_chars is None
        else max_chars
    )

    if not observations:

        return "_No observation payloads (empty list)._\n"

    chunks = []

    for i, ob in enumerate(observations, start=1):

        if isinstance(ob, dict):

            dumped = json.dumps(
                ob,
                indent=2,
                ensure_ascii=False,
            )

            label = ""

            src = ob.get("source")

            err = ob.get("error")

            if src == "online_api":

                if err:

                    label = "**Live weather API** (`wttr.in`) — **error**."

                else:

                    label = "**Live weather API** (`wttr.in`) — **response**."

                city = ob.get("city")

                if city:

                    label += f" City argument: `{city}`."

            else:

                label = "**Structured observation** (non-weather JSON)."

            chunks.append(
                f"**Observation {i}** — {label}\n```json\n{dumped}\n```",
            )

        else:

            blob = str(ob).strip()

            passages = blob

            if cap is not None and len(passages) > cap:

                passages = (
                    passages[:cap].rstrip()
                    + "\n\n…_(truncated — cap EVAL_REPORT_BODY_CHAR_CAP)_"
                )

            if used_rag:

                rag_record = dict(_RAG_REPORT_META)

                rag_record["source"] = "rag"

                rag_record["retrieved_passages"] = passages

                dumped_r = json.dumps(
                    rag_record,
                    indent=2,
                    ensure_ascii=False,
                )

                chunks.append(
                    f"**Observation {i}** — **RAG retrieval** "
                    "(Faiss over embedded knowledge lines — same blob phase-2 saw)\n"
                    f"```json\n{dumped_r}\n```",
                )

            else:

                if cap is not None and len(blob) > cap:

                    blob = (
                        blob[:cap].rstrip()
                        + "\n\n…_(truncated — cap EVAL_REPORT_BODY_CHAR_CAP)_"
                    )

                chunks.append(
                    f"**Observation {i}** — **Text observation**\n"
                    f"{_fenced_answer(blob, max_chars=cap)}",
                )

    return "\n\n".join(chunks) + "\n"


def _tool_retrieval_outputs_section_md(full):

    """Report body: flags + verbatim payloads for external tool/RAG."""

    lines = [
        "### Tool and RAG retrieval outputs\n\n",
        "Verbatim payloads passed into phase-2 synthesis as **OBSERVATIONS**. "
        "Both are shown in **`json`** form when applicable: **`used_tool`** → "
        "live **`wttr.in`** payload (structured dict); **`used_rag`** → merged "
        "passages plus corpus metadata (`data/knowledge_base.txt`, Faiss, "
        "`all-MiniLM-L6-v2`, `top_k=3`).\n\n",
    ]

    for title, ut, ur, obs in (
        (
            "Planner",
            full["planner_used_tool"],
            full["planner_used_rag"],
            full["planner_observations"],
        ),
        (
            "Executor",
            full["executor_used_tool"],
            full["executor_used_rag"],
            full["executor_observations"],
        ),
    ):

        lines.append(f"#### {title}\n\n")

        lines.append(f"- **`used_tool`:** `{ut}`\n")

        lines.append(f"- **`used_rag`:** `{ur}`\n\n")

        if ut or ur:

            lines.append(
                "**Recorded output(s):**\n\n",
            )

            if obs:

                lines.append(
                    _observations_payload_md(
                        obs,
                        used_tool=ut,
                        used_rag=ur,
                    ),
                )

            else:

                lines.append(
                    "_**Warning:** `used_tool` / `used_rag` is True but the "
                    "observation list is empty — check pipeline wiring._\n\n",
                )

        elif obs:

            lines.append(
                "_No tool/RAG flags, but observations list is non-empty "
                "(unusual — showing raw payloads):_\n\n",
            )

            lines.append(
                _observations_payload_md(
                    obs,
                    used_tool=False,
                    used_rag=False,
                ),
            )

        else:

            lines.append(
                "_No external calls; observation list empty for this agent._\n\n",
            )

    return "".join(lines)


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


def _structured_payload_preview(ll_bundle, structured_flag):

    if (
        not structured_flag
        or not isinstance(ll_bundle, dict)
        or ll_bundle.get("skipped")
    ):

        return ""

    record = ll_bundle.get("parsed_record")

    if not isinstance(record, dict):

        return ""

    qa = json.dumps(record, indent=2, ensure_ascii=False)

    return (
        "\n**Emitted record (validated when schema-ok):**\n```json\n"
        f"{qa}\n```\n"
    )


def _structured_layer_summary(structured_flag, ll_bundle):

    if not structured_flag:

        return (
            "**Row setting:** structured SLM conformance pass **off** "
            "(dataset/default). Programmatic JSON still attached in telemetry."
        )

    if not isinstance(ll_bundle, dict):

        return "**Telemetry:** malformed bundle (dict expected)."

    if ll_bundle.get("skipped"):

        return (
            "**Structured SLM:** skipped — telemetry records canonical JSON "
            "from deterministic packaging only (`llm_attempted_this_case`=false)."
        )

    v1 = ll_bundle.get("valid_first_attempt")

    vf = ll_bundle.get("valid_final")

    rep = ll_bundle.get("repairs_used", 0)

    r1 = "yes" if v1 else "no"

    rf = "yes" if vf else "no"

    parts = [
        f"- First-sample schema-valid: **{r1}** (`valid_first_attempt`).",
        f"- After validator + repair loop: **{rf}** (`valid_final`).",
        f"- Repair iterations recorded: **{rep}** (`repairs_used`).",
    ]

    prv = _structured_payload_preview(ll_bundle, True)

    if prv:

        parts.append(prv.strip())

    if v1 is False and vf is True:

        parts.append(
            "- Outcome: **repair recovered** conformant JSON after first failure."
        )

    elif vf is False:

        parts.append(
            "- Outcome: **still failing** schema after repairs — see raw blobs in telemetry."
        )

    return "\n".join(parts)


PIPELINE_LAYERS_CONCEPT_MD = """## Measurement layout

Each testcase below corresponds to **one row** from the evaluation dataset. Scores refer to **the keyword rubric** on that row’s positive/negative phrase lists (`N₊` / `N₋` counts are stated per case).

**Stages (text artefacts in order):** (1) single-pass baseline answer → (2) planner trajectory (pre-judge / no judge) → (3) executor trajectory → (4) post-judge final answer → (5) optional structured SLM JSON (schema validation + repair telemetry).

### End-to-end flow (matches the implemented pipeline)

```mermaid
flowchart TD
  Q["Query + benchmark category"] --> SP["Single-pass baseline<br/>one LLM, direct answer"]
  Q --> PL["Planner ReAct: Thought → Action → Observation"]
  Q --> EX["Executor ReAct: Thought → Action → Observation"]
  PL --> J["Judge: planner vs executor<br/>self-consistency"]
  EX --> J
  J --> ST["Structured output: validator + optional repair"]
  ST --> OUT["Final answer + JSON telemetry"]
  SP --> RUB["Keyword rubric per stage"]
  OUT --> RUB
```

"""


def _pipeline_case_metrics_md(
    *,
    pk_single,
    pk_planner,
    pk_exec,
    pk_multi,
    n_pos_kw,
    n_neg_kw,
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

    baseline_net = pk_single[0]

    def row(label, pk, delta_vs_single):

        sc, mp, mn, _, nc, pos_w, neg_w = pk

        d_cell = (
            "—"
            if delta_vs_single is None
            else f"{delta_vs_single:+.1f}"
        )

        p_cell = (
            f"{len(mp)}/{n_pos_kw}"
            if n_pos_kw
            else "—"
        )

        n_denom = max(1, int(n_neg_kw))

        n_cell = f"{len(mn)}/{n_denom}"

        return (
            f"| {label} | {sc}% | {d_cell} | "
            f"{p_cell} | {round(pos_w, 2)}% | "
            f"{n_cell} | {round(neg_w, 2)}% | {nc} |\n"
        )

    body = "".join(
        (
            row(
                "Single-pass baseline",
                pk_single,
                None,
            ),
            row(
                "Planner (pre-judge)",
                pk_planner,
                round(
                    pk_planner[0] - baseline_net,
                    1,
                ),
            ),
            row(
                "Executor",
                pk_exec,
                round(
                    pk_exec[0] - baseline_net,
                    1,
                ),
            ),
            row(
                "Post-judge final",
                pk_multi,
                round(
                    pk_multi[0] - baseline_net,
                    1,
                ),
            ),
        ),
    )

    struct_txt = _structured_layer_summary(
        structured_flag,
        ll_bundle,
    )

    key_line = ""

    if n_pos_kw:

        key_line += (
            f"`+weight` divides +hits by **{n_pos_kw}** (dataset positives). "
        )

    else:

        key_line += (
            "**No positive phrases:** +weight forced to **0%** "
            "(no divisor). "
        )

    key_line += (
        f"`−penalty` uses divisor **max(1, N₋)** = **{max(1, int(n_neg_kw))}** "
        "for this row. "
        "**Net** = `max(0, round(+weight − −penalty, 1))` "
        "(same as `_rubric_breakdown`)."
    )

    return (
        "### Layer metrics (this testcase)\n\n"
        f"{key_line}\n\n"
        "#### Keyword rubric by pipeline artifact\n\n"
        "| Artifact | Net % | Δ vs single | "
        "+hits/N₊ | +weight | −hits/N₋ | −penalty | Answer chars |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|\n"
        f"{body}\n"
        "#### Tool / retrieval flags (boolean telemetry)\n\n"
        "| Role | used_tool | used_rag |\n"
        "|---|:---:|:---:|\n"
        f"| Planner | {planner_tool} | {planner_rag} |\n"
        f"| Executor | {exec_tool} | {exec_rag} |\n"
        f"| Combined (planner ∨ executor) | {combined_tool} | {combined_rag} |\n\n"
        "#### Judge outcome (planner vs executor narratives)\n\n"
        f"{judge_label}\n\n"
        "#### Structured layer (SLM validation / repair)\n\n"
        f"{struct_txt}\n\n"
        "#### Latency (wall-clock in driver)\n\n"
        f"Single-pass **{baseline_latency}s**; multi-agent end-to-end "
        f"**{multi_latency}s**.\n\n"
    )


class Evaluator:

    def __init__(self, pipeline):

        self.pipeline = pipeline

    def score(self, answer, positive, negative):

        s, _, _, _, _, _, _ = _rubric_breakdown(
            answer,
            positive,
            negative,
        )

        return s

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

            pk_single = (
                _rubric_breakdown(
                    baseline["answer"],
                    positives,
                    negatives,
                )
            )

            pk_multi = (
                _rubric_breakdown(
                    full["answer"],
                    positives,
                    negatives,
                )
            )

            pk_planner = (
                _rubric_breakdown(
                    full["answer_no_judge"],
                    positives,
                    negatives,
                )
            )

            pk_exec = (
                _rubric_breakdown(
                    full["executor_answer"],
                    positives,
                    negatives,
                )
            )

            s_score = pk_single[0]

            m_score = pk_multi[0]

            p_only = pk_planner[0]

            e_score = pk_exec[0]

            for slug, pk in (
                ("single-pass", pk_single),
                ("planner_no_judge", pk_planner),
                ("executor", pk_exec),
                ("multi_final", pk_multi),
            ):

                sc, mp_hit, mn_hit, miss_pos, nc, pw, nw = pk

                rubric_log(
                    (
                        f"case {idx}/{n_cases} [{category}] {slug}: "
                        f"net={sc}% (+weight={round(pw, 2)}% "
                        f"−penalty={round(nw, 2)}%) "
                        f"answer_chars={nc} "
                        f"+hits={len(mp_hit)}/{len(positives)} "
                        f"{mp_hit!s} -hits={mn_hit!s} +miss={miss_pos!s}"
                    ),
                )

            judge_label = _judge_trajectory_label(
                full["planner_answer"],
                full["executor_answer"],
                full["answer"],
            )

            layers_md = _pipeline_case_metrics_md(
                pk_single=pk_single,
                pk_planner=pk_planner,
                pk_exec=pk_exec,
                pk_multi=pk_multi,
                n_pos_kw=len(positives),
                n_neg_kw=len(negatives),
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
                    f"{p_only}%",
                    f"{e_score}%",
                    f"{m_score}%",
                    f"{full['latency']:.2f}s",
                    full["used_tool"],
                    full["used_rag"],
                ],
            )

            structured_pipeline_json = json.dumps(
                full.get(
                    "structured_pipeline",
                    {},
                ),
                indent=2,
                ensure_ascii=False,
                default=str,
            )

            canonical_structured_fence = (
                full.get(
                    "canonical_structured_dump",
                )
                or "{}"
            )

            rubric_diag_md = _rubric_diagnostics_md(
                [
                    (
                        "Single-pass",
                        pk_single[0],
                        pk_single[4],
                        pk_single[1],
                        pk_single[2],
                        pk_single[3],
                        pk_single[5],
                        pk_single[6],
                    ),
                    (
                        "Planner (pre-judge)",
                        pk_planner[0],
                        pk_planner[4],
                        pk_planner[1],
                        pk_planner[2],
                        pk_planner[3],
                        pk_planner[5],
                        pk_planner[6],
                    ),
                    (
                        "Executor",
                        pk_exec[0],
                        pk_exec[4],
                        pk_exec[1],
                        pk_exec[2],
                        pk_exec[3],
                        pk_exec[5],
                        pk_exec[6],
                    ),
                    (
                        "Multi (post-judge)",
                        pk_multi[0],
                        pk_multi[4],
                        pk_multi[1],
                        pk_multi[2],
                        pk_multi[3],
                        pk_multi[5],
                        pk_multi[6],
                    ),
                ],
            )

            delta_kw = round(
                m_score - s_score,
                1,
            )

            tool_outputs_md = _tool_retrieval_outputs_section_md(full)

            md_sections.append(
                f"""## {category}
{proof_line}
### Query
{query}

{layers_md}

{tool_outputs_md}

### Narrative outputs (pipeline order)
Keyword-rubric Δ for final vs single (**post-judge net − single net**): **`{delta_kw:+.1f}`** points — numbers above use `N₊`={len(positives)}, `N₋`={len(negatives)}.

#### Stage 1 — Single-pass baseline
{_fenced_answer(baseline["answer"])}

#### Stage 2 — Planner trajectory (same text as «without judge»)
{_fenced_answer(full["answer_no_judge"])}

#### Stage 3 — Executor trajectory (pre-judge)
{_fenced_answer(full["executor_answer"])}

#### Stage 4 — Post-judge final
{_fenced_answer(full["answer"])}

{rubric_diag_md}

### Planner ReAct trace
```
{_snippet(full["planner_react_trace"])}
```

### Executor ReAct trace
```
{_snippet(full["executor_react_trace"])}
```

### Structured output (verbatim, not truncated)

The object below matches **`structured_pipeline`** from the benchmark run:
**`programmatic_safe_json`** is the deterministic pydantic envelope from the
judge-final narrative (trust this for non-empty **`answer`** when the SLM
`parsed_record` is wrong or incomplete). **`llm`** holds SLM completions
(`raw_first`, `parsed_record`, etc.) without clipping.

```json
{structured_pipeline_json}
```

#### `canonical_structured_dump` (same envelope as compact JSON text)

```json
{canonical_structured_fence}
```

"""
            )

        tool_rate = ""

        tool_frac = ""

        if tool_checked:

            tool_pct = (
                100.0 * tool_hits / tool_checked
            )

            tool_rate = "%.1f" % tool_pct

            tool_frac = (
                f"`used_tool` matched dataset expectation in "
                f"**{tool_hits}/{tool_checked}** rows "
                f"({tool_rate}%); rows counted are categories with "
                f"a defined expectation in `_EXPECTED_USED_TOOL`."
            )

        else:

            tool_rate = "n/a"

            tool_frac = (
                "**0** labelled expectations — denominator empty "
                "(no category in `_EXPECTED_USED_TOOL`)."
            )

        rag_frac = ""

        rag_rate = ""

        if rag_checked:

            rag_pct = (
                100.0 * rag_hits / rag_checked
            )

            rag_rate = "%.1f" % rag_pct

            rag_frac = (
                f"**{rag_hits}/{rag_checked}** `rag_*` rows with "
                f"`used_rag=True` ({rag_rate}%)."
            )

        else:

            rag_rate = "n/a"

            rag_frac = (
                "**0** `rag_*` categories in this run — no RAG engagement rate."
            )

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

        json_first_frac = ""

        if json_first_pass:

            jf_ok = sum(
                1 for x in json_first_pass if x
            )

            json_first_frac = (
                f"**{jf_ok}/{len(json_first_pass)}** structured-eval rows "
                f"passed schema on first structured LLM completion "
                f"({first_json}%)."
            )

        else:

            json_first_frac = "**n/a** — no structured SLM passes recorded."

        json_final_frac = ""

        if json_after_repair:

            ja_ok = sum(
                1 for x in json_after_repair if x
            )

            json_final_frac = (
                f"**{ja_ok}/{len(json_after_repair)}** rows schema-valid "
                f"after validator + repair attempts ({repaired_json}%)."
            )

        else:

            json_final_frac = "**n/a** — repair-tracked bundles absent."

        if structured_repairs:

            repair_avg = "%.2f" % (
                sum(structured_repairs)
                / len(structured_repairs),
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

        sum_planner = sum(
            planner_only_scores,
        )

        report_intro = (
            f"""# Benchmark report ({EVALUATION_REPORT_PATH.name})

This annex supports the **course project proposal** (`Proposal.md`): ReAct-style agents, multi-agent comparison, judge-based self-consistency, retrieval/tool grounding, structured JSON with validation/repair, and resource-aware measurement (latency, RSS).

**Dataset:** **`{dataset_path}`** — **{n_cases}** testcase rows. Each appendix section records **answers, ReAct traces, tool/RAG usage, judge selection, and structured-output telemetry** so results can be read as evidence for each proposal theme (not only headline percentages).

**Scoring:** Per-row **Net %** is the keyword rubric from `positive_keywords` / `negative_keywords` (substring match after light normalization — see `_rubric_normalize` in `evaluation.py`). This operationalises **task accuracy** for the coursework benchmark; aggregate **means** are **unweighted** averages of those Net % values. Structured-output rates (first-pass vs after repair) apply only to rows where the structured SLM pass ran.

**Reading order:** (1) **Proposal ↔ this artefact** (cross-walk to `Proposal.md`) → (2) **Aggregate metrics** and summary tables → (3) **Per-case appendix** (Mermaid flow under *Measurement layout*, narratives, traces, rubric breakdown, JSON).

"""
        )

        metrics_block = (
            "## Aggregate metrics\n\n"
            "| Metric | Result |\n|---|---|\n"
            "| Mean Net % — single-pass | "
            f"**(Σ single / N)** = `{sum_single:.1f}/{n_cases}` → **{avg_single:.1f}%** |\n"
            "| Mean Net % — post-judge final | "
            f"**(Σ final / N)** = `{sum_multi:.1f}/{n_cases}` → **{avg_multi:.1f}%** |\n"
            "| Mean Net % — planner trajectory only | "
            f"**(Σ planner / N)** = `{sum_planner:.1f}/{n_cases}` → "
            f"**{avg_planner_only:.1f}%** |\n"
            "| Tool expectation check | "
            f"{tool_frac} |\n"
            "| RAG engagement (`rag_*` rows) | "
            f"{rag_frac} |\n"
            "| JSON valid — first structured sample | "
            f"{json_first_frac} |\n"
            "| JSON valid — after repairs | "
            f"{json_final_frac} |\n"
            "| Mean repair iterations | "
            f"**{repair_avg}** over **{len(structured_repairs)}** "
            "structured-eval rows with repair accounting |\n"
            "| RSS (MB) start / end | "
            f"{rss_open if rss_open is not None else 'n/a'} / "
            f"{rss_close if rss_close is not None else 'n/a'} |\n\n"
        )

        tbl_single = "## Single-pass baseline table\n\n" + tabulate(
            single_rows,
            headers=[
                "category",
                "net_%",
                "latency_s",
            ],
            tablefmt="github",
        )

        tbl_multi = "\n\n## Multi-agent per-row scores\n\nKeyword **Net %** by stage (same rubric as the appendix).\n\n" + tabulate(
            multi_rows,
            headers=[
                "category",
                "planner_%",
                "executor_%",
                "final_%",
                "latency_s",
                "tool?",
                "rag?",
            ],
            tablefmt="github",
        )

        mapping_md = """

## Proposal ↔ this artefact

Cross-walk to **`Proposal.md`** (problem statement, approach, evaluation plan, deliverables). Use the **per-case appendix** for primary evidence (text, traces, JSON).

| Proposal item | Section in this report |
|---|---|
| ReAct: Thought → Action → Observation | **Planner ReAct trace** / **Executor ReAct trace** in each case; Actions show tool / `rag` / no-op. |
| Multi-agent “debate” (independent trajectories) | **Stage 2–3** narratives; columns **planner_%** vs **executor_%** vs **final_%**. |
| Self-consistency / judge | **Stage 4 — Post-judge final**; judge selection in the pipeline layer table; **Mean Net % — post-judge final** vs **planner trajectory only** (ablation-style comparison). |
| Structured output: schema validation + repair | Aggregate rows **JSON valid — first** / **after repairs**; **Mean repair iterations**; **Structured output** JSON blocks per case. |
| RAG (optional grounding) | Column **rag?**; **RAG engagement**; retrieval lines in traces and tool/RAG verbatim sections when applicable. |
| Tool usage efficiency | Column **tool?**; **Tool expectation check**; live tool/API lines in traces where used. |
| Single-pass vs multi-agent | **Single-pass baseline table** vs **Multi-agent** table; per-case **Δ** (final vs single). |
| Latency / memory (resource analysis) | **latency_s** columns; **RSS** in aggregate metrics. |
| Failure analysis | Low scores: see **Keyword lists** subsection (+/− hits, missed positives); invalid JSON: structured telemetry and repair outcome. |
| Modular evaluation (planner / executor / judge / validator) | Separate stage scores and traces; structured bundle distinguishes deterministic envelope vs SLM parse. |

"""

        appendix = (
            PIPELINE_LAYERS_CONCEPT_MD
            + "\n## Per-case appendix\n\n"
            + "".join(md_sections)
        )

        full_report = (
            report_intro
            + mapping_md
            + metrics_block
            + tbl_single
            + tbl_multi
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
                    "net_%",
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
                    "planner_%",
                    "executor_%",
                    "final_%",
                    "latency_s",
                    "tool?",
                    "rag?",
                ],
                tablefmt="github",
            ),
        )

        return EVALUATION_REPORT_PATH
