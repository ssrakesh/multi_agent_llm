import time

from llm import LLM

from config import *

from logger import (
    section,
    sys_log,
    proof_log,
    benchmark_log,
    stage_log
)

from agents.planner import (
    run_react_agent
)

from agents.judge import (
    judge_agent
)

from agents.executor import (
    StructuredOutputAgent
)


# ============================================================
# MULTI-AGENT PIPELINE
# ============================================================

class MultiAgentPipeline:

    def __init__(
        self,
        tools,
        rag_system
    ):

        self.tools = tools

        self.rag_system = rag_system

    # ========================================================
    # SINGLE AGENT BASELINE
    # ========================================================

    def run_single_agent(
        self,
        query
    ):

        section(
            "SINGLE AGENT BASELINE"
        )

        stage_log(
            "BASELINE",
            f"Processing query -> {query}"
        )

        start = time.time()

        # ----------------------------------------------------
        # LOAD SINGLE MODEL
        # ----------------------------------------------------

        sys_log(
            "Loading baseline model"
        )

        model = LLM(
            AGENT_MODELS["planner"]
        )

        # ----------------------------------------------------
        # DIRECT INFERENCE
        # ----------------------------------------------------

        proof_log(
            "Running direct single-model inference"
        )

        answer = model.generate(
            query
        )

        # ----------------------------------------------------
        # UNLOAD MODEL
        # ----------------------------------------------------

        model.unload()

        runtime = (
            time.time() - start
        )

        benchmark_log(
            f"Single-agent runtime: "
            f"{runtime:.2f}s"
        )

        return {
            "mode": "single_agent",
            "query": query,
            "answer": answer,
            "latency": runtime,
            "used_tool": False,
            "used_rag": False
        }

    # ========================================================
    # MULTI-AGENT PIPELINE
    # ========================================================

    def run_multi_agent(
        self,
        query
    ):

        section(
            "MULTI-AGENT PIPELINE"
        )

        stage_log(
            "PIPELINE",
            f"Processing query -> {query}"
        )

        total_start = time.time()

        # ====================================================
        # PLANNER AGENT
        # ====================================================

        section(
            "PLANNER AGENT"
        )

        stage_log(
            "PLANNER",
            "Loading planner model"
        )

        planner_start = time.time()

        planner_llm = LLM(
            AGENT_MODELS["planner"]
        )

        planner_result = (
            run_react_agent(
                planner_llm,
                query,
                self.tools,
                self.rag_system,
                MAX_AGENT_STEPS
            )
        )

        planner_llm.unload()

        planner_time = (
            time.time() -
            planner_start
        )

        benchmark_log(
            f"Planner runtime: "
            f"{planner_time:.2f}s"
        )

        # ====================================================
        # EXECUTOR AGENT
        # ====================================================

        section(
            "EXECUTOR AGENT"
        )

        stage_log(
            "EXECUTOR",
            "Loading executor model"
        )

        executor_start = time.time()

        executor_llm = LLM(
            AGENT_MODELS["executor"]
        )

        executor_result = (
            run_react_agent(
                executor_llm,
                query,
                self.tools,
                self.rag_system,
                MAX_AGENT_STEPS
            )
        )

        executor_llm.unload()

        executor_time = (
            time.time() -
            executor_start
        )

        benchmark_log(
            f"Executor runtime: "
            f"{executor_time:.2f}s"
        )

        # ====================================================
        # JUDGE AGENT
        # ====================================================

        section(
            "JUDGE AGENT"
        )

        stage_log(
            "JUDGE",
            "Loading judge model"
        )

        judge_start = time.time()

        judge_llm = LLM(
            AGENT_MODELS["judge"]
        )

        candidate_answers = [

            planner_result[
                "answer"
            ],

            executor_result[
                "answer"
            ]
        ]

        proof_log(
            "Self-consistency evaluation started"
        )

        final_answer = (
            judge_agent(
                judge_llm,
                query,
                candidate_answers
            )
        )

        judge_time = (
            time.time() -
            judge_start
        )

        judge_llm.unload()

        benchmark_log(
            f"Judge runtime: "
            f"{judge_time:.2f}s"
        )

        # ====================================================
        # STRUCTURED OUTPUT
        # ====================================================

        section(
            "STRUCTURED OUTPUT"
        )

        json_output = (
            StructuredOutputAgent
            .generate_json(
                query,
                final_answer
            )
        )

        # ====================================================
        # TOTAL METRICS
        # ====================================================

        total_time = (
            time.time() -
            total_start
        )

        benchmark_log(
            f"Total pipeline runtime: "
            f"{total_time:.2f}s"
        )

        # ====================================================
        # PROOF LOGS
        # ====================================================

        proof_log(
            "Planner/Executor/Judge orchestration completed"
        )

        proof_log(
            "Sequential heterogeneous SLM execution used"
        )

        proof_log(
            "Self-consistency reasoning applied"
        )

        # ----------------------------------------------------
        # RAG PROOF
        # ----------------------------------------------------

        if (
            planner_result[
                "used_rag"
            ]
            or
            executor_result[
                "used_rag"
            ]
        ):

            proof_log(
                "RAG grounding confirmed"
            )

        # ----------------------------------------------------
        # TOOL PROOF
        # ----------------------------------------------------

        if (
            planner_result[
                "used_tool"
            ]
            or
            executor_result[
                "used_tool"
            ]
        ):

            proof_log(
                "Tool usage confirmed"
            )

        # ----------------------------------------------------
        # TOOL RESTRAINT
        # ----------------------------------------------------

        if (
            not planner_result[
                "used_tool"
            ]
            and
            not executor_result[
                "used_tool"
            ]
        ):

            proof_log(
                "Tool restraint behavior observed"
            )

        # ====================================================
        # FINAL OUTPUT
        # ====================================================

        section(
            "FINAL OUTPUT"
        )

        print(json_output)

        return {
            "mode": "multi_agent",
            "query": query,
            "answer": final_answer,
            "latency": total_time,
            "used_tool": (
                planner_result[
                    "used_tool"
                ]
                or
                executor_result[
                    "used_tool"
                ]
            ),
            "used_rag": (
                planner_result[
                    "used_rag"
                ]
                or
                executor_result[
                    "used_rag"
                ]
            ),
            "planner_tools":
                planner_result[
                    "selected_tools"
                ],
            "executor_tools":
                executor_result[
                    "selected_tools"
                ],
            "structured_output":
                json_output
        }