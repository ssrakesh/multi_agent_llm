from llm import LLM
from config import *
from agents.planner import run_react_agent
from agents.judge import judge_agent
from agents.validator import Validator
from agents.repair import RepairAgent
from agents.executor import StructuredOutputAgent

class MultiAgentPipeline:

    def __init__(self, tools, rag_system):

        self.tools = tools
        self.rag_system = rag_system

    def run(self, query):

        planner_llm = LLM(
            AGENT_MODELS["planner"]
        )

        planner_result = run_react_agent(
            planner_llm,
            query,
            self.tools,
            self.rag_system,
            MAX_AGENT_STEPS
        )

        planner_llm.unload_model()

        executor_llm = LLM(
            AGENT_MODELS["executor"]
        )

        executor_result = run_react_agent(
            executor_llm,
            query,
            self.tools,
            self.rag_system,
            MAX_AGENT_STEPS
        )

        executor_llm.unload_model()

        candidate_answers = [
            planner_result["answer"],
            executor_result["answer"]
        ]

        judge_llm = LLM(
            AGENT_MODELS["judge"]
        )

        final_answer = judge_agent(
            judge_llm,
            query,
            candidate_answers
        )

        json_output = (
            StructuredOutputAgent.generate_json(
                judge_llm,
                query,
                final_answer,
                True,
                True
            )
        )

        validated, ok = Validator.validate(
            json_output
        )

        if not ok:

            repaired = RepairAgent.repair(
                judge_llm,
                json_output,
                validated
            )

            validated, ok = Validator.validate(
                repaired
            )

        judge_llm.unload_model()

        return validated
