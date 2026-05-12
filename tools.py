import requests

from logger import (
    proof_log,
    stage_log
)

def weather_tool(city):

    stage_log(
        "WEATHER",
        f"Fetching live weather -> {city}"
    )

    try:

        response = requests.get(
            f"https://wttr.in/{city}?format=3",
            timeout=10
        )

        proof_log(
            "External online API used"
        )

        return {
            "source":"online_api",
            "city":city,
            "response":response.text
        }

    except Exception as e:

        return {
            "source":"online_api",
            "error":str(e)
        }

def python_tool(code):

    local = {}

    try:

        exec(code, {}, local)

        return str(local)

    except Exception as e:

        return str(e)

def kb_lookup_tool(query, kb):

    results = []

    for item in kb:

        if query.lower() in item.lower():
            results.append(item)

    if not results:
        return "No knowledge found"

    return "\n".join(results[:3])
