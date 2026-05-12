import time

from llm import LLM

from config import *

from prompts import (
    PLANNER_PROMPT,
    EXECUTOR_PROMPT
)

from logger import (
    section,
    proof_log,
    benchmark_log
)

from agents.planner import (
    run_react_agent
)

from agents.judge import (
    judge_agent
)

class MultiAgentPipeline:

    def __init__(self, tools, rag_system):

        self.tools = tools
        self.rag_system = rag_system

    def run_single_agent(self, query):

        section(
            "SINGLE AGENT BASELINE"
        )

        start = time.time()

        model = LLM(
            AGENT_MODELS["planner"]
        )

        answer = model.generate(query)

        model.unload()

        runtime = (
            time.time() - start
        )

        benchmark_log(
            f"Single-agent runtime: {runtime:.2f}s"
        )

        return {
            "answer": answer,
            "latency": runtime
        }

    def run_multi_agent(self, query):

        section(
            "MULTI AGENT PIPELINE"
        )

        total_start = time.time()

        planner = LLM(
            AGENT_MODELS["planner"]
        )

        planner_result = run_react_agent(
            planner,
            query,
            self.tools,
            self.rag_system,
            PLANNER_PROMPT
        )

        planner.unload()

        executor = LLM(
            AGENT_MODELS["executor"]
        )

        executor_result = run_react_agent(
            executor,
            query,
            self.tools,
            self.rag_system,
            EXECUTOR_PROMPT
        )

        executor.unload()

        final_answer = judge_agent(
            query,
            [
                planner_result["answer"],
                executor_result["answer"]
            ]
        )

        runtime = (
            time.time() - total_start
        )

        proof_log(
            "Multi-agent orchestration completed"
        )

        return {
            "answer": final_answer,
            "latency": runtime,
            "used_tool":
                planner_result["used_tool"]
                or
                executor_result["used_tool"],
            "used_rag":
                planner_result["used_rag"]
                or
                executor_result["used_rag"],
            "planner_observations":
                planner_result["observations"],
            "executor_observations":
                executor_result["observations"]
        }
