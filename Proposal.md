# Project Proposal

## Title:  Adaptive Multi-Agent LLM System with ReAct Reasoning, Self-Consistency, and Reliable Structured Outputs

***Course*: LLMs: A Hands on Approach, CCE IISc**  
**Team Members:** "Rakesh Srinath" <srakesh@ssdi.sharp.co.in>, "Dhananjay Singh" <sdhananjay@ssdi.sharp.co.in>  
**Date:** 04-04-2026

---

## 1. Problem Statement

**Problem:**  
LLM-based agent systems often lack true iterative reasoning, make inefficient tool usage decisions, and generate unreliable structured outputs, limiting their applicability in real-world systems.

**Relevance:**  
Modern AI systems (assistants, automation pipelines, APIs) require:
- Multi-step reasoning (beyond single-pass generation)  
- Efficient and selective tool usage  
- Reliable structured outputs (e.g., valid JSON)  

However, existing approaches:
- Rely on single-agent or single-pass prompting  
- Do not implement reasoning loops (ReAct)  
- Produce inconsistent or invalid structured outputs  

**Domain:**  
Agents, Reasoning (ReAct, Self-Consistency), Structured Output, Inference Optimization

---

## 2. Proposed Approach

**Core Idea:**  
We propose a **multi-agent LLM system** that integrates:

1. **ReAct-based iterative reasoning**  
   - Thought → Action → Observation loop  
   - Enables dynamic and grounded decision-making  

2. **Multi-agent debate mechanism**  
   - Multiple agents generate independent reasoning trajectories  
   - Improves robustness through diverse reasoning paths  

3. **Self-consistency selection**  
   - Final output selected using majority voting or a judge agent  
   - Reduces hallucinations and reasoning errors  

4. **Structured output generation with validation and repair**  
   - JSON schema-based validation  
   - Automatic repair loop for invalid outputs  

5. **Retrieval-Augmented Generation (RAG)**
    - The system incorporates a retrieval module to provide external knowledge grounding  
    - The agent dynamically decides when to invoke retrieval based on the query  
    - Retrieved documents are used as context for reasoning and answer generation  

---

### Model Selection (Flexible)

The exact LLM to be used has not been finalized at this stage. The final model will be selected based on available hardware resources (e.g., GPU VRAM) and performance considerations. Candidate models include:

- Mistral 7B v0.3  
- Gemma (2B / 7B variants)  
- Qwen 2.5 (3B–7B)  
- Phi-3  

---

**Project Type:**  
Working system + experimental evaluation  

---

**Datasets / Tasks:**
- Arithmetic and symbolic reasoning dataset (generated)  
- Tool-based queries (calculator, API simulation)  
- Structured output dataset (JSON generation tasks)  

---

**What is Novel:**  
- Combines **ReAct reasoning + multi-agent debate + self-consistency + structured output validation** in a unified system  
- Evaluates how multi-agent reasoning improves tool usage and output reliability  
- Supports optional retrieval-based grounding (RAG)  
- Designed to operate under **resource constraints (e.g., 8GB VRAM)**  

---

## 3. Related Work

| # | Reference | How this project differs |
|--|----------|------------------------|
| 1 | ReAct: Synergizing Reasoning and Acting (Yao et al., 2023) | Extends single-agent reasoning to multi-agent debate |
| 2 | Self-Consistency Improves Chain-of-Thought (Wang et al., 2022) | Uses full agent trajectories instead of sampling |
| 3 | Function calling frameworks | Do not model reasoning loops or tool decision efficiency |
| 4 | Structured output / constrained decoding methods | Not integrated with agent-based reasoning |

---

## 4. Expected Deliverables

- **Code repository:**
  - Multi-agent pipeline (planner, executor, judge, validator, repair)
  - Tool integration system
  - Structured output validation + repair loop
  - Modular LLM interface (supports multiple models)
  - Modular architecture enabling independent evaluation of planner, executor, judge, and validator components  

- **Report:**
  - Experimental comparisons (single-agent vs multi-agent)
  - Model comparison across selected LLMs
  - Ablation studies of system components  

- **Demo:**
  - CLI or web-based interface  
  - Visualization of reasoning steps (Thought → Action → Observation)

---

## 5. Evaluation Plan

**Metrics:**

1. **Task Accuracy**
   - Correctness of final outputs  

2. **Tool Usage Efficiency**
   - Correct vs unnecessary tool calls  

3. **JSON Validity Rate**
   - Percentage of valid structured outputs  

4. **Reasoning Effectiveness**
   - Success rate on multi-step reasoning tasks  

5. **Resource Usage**
   - Memory usage and inference latency across models  

---

**Baselines:**
- Single-pass LLM (no agent)  
- Single-agent ReAct (no debate)  
- Multi-agent without self-consistency  

---

**Experiments:**
- Single-agent vs Multi-agent system  
- Without vs With self-consistency  
- Without vs With validation/repair loop  
- Comparison across different models  
- Evaluation with and without RAG (if implemented)  

---

**Ablation Studies:**
- Remove self-consistency → measure accuracy drop  
- Remove validator → measure JSON failure rate  
- Remove debate → compare reasoning quality  

---

**Failure Analysis:**
We will analyze common failure cases including incorrect reasoning paths, tool misuse, retrieval errors (if RAG is used), and invalid structured outputs.

---

**Resource Analysis:**
We evaluate trade-offs between reasoning performance and computational cost (latency, memory usage).

---

## 6. Timeline

| Week | Plan |
|------|------|
| 1 | Literature review, base ReAct agent |
| 2 | Multi-agent + debate implementation |
| 3 | Structured output + validation |
| 4 | Model selection + experiments |
| 5 | Evaluation, report, and demo |

---

## Summary

This project aims to build a **robust, efficient, and resource-aware multi-agent LLM system** that improves reasoning accuracy, tool usage, and structured output reliability.