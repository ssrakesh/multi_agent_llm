import requests

def weather_tool(city):

    try:
        return requests.get(
            f"https://wttr.in/{city}?format=3",
            timeout=10
        ).text
    except Exception as e:
        return str(e)

def python_tool(code):

    try:
        local = {}
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
