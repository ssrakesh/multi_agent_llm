SYSTEM_PROMPT = '''
You are an intelligent ReAct multi-agent system.

Available tools:
1. rag
2. kb_lookup
3. python

Strict format:

THOUGHT:
ACTION:
INPUT:

or

FINAL:
'''

JSON_PROMPT = '''
Convert to VALID JSON.

Question: {query}
Answer: {answer}

Return ONLY JSON.

Format:
{{
    "query": "...",
    "answer": "...",
    "used_tool": true,
    "used_rag": true
}}
'''

REPAIR_PROMPT = '''
Fix invalid JSON.

Error:
{error}

JSON:
{bad_json}

Return ONLY corrected JSON.
'''

JUDGE_PROMPT = '''
Question:
{query}

Candidate Answers:
{answers}

Select best answer.
Return ONLY answer text.
'''
