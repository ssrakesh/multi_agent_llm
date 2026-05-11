def kb_lookup_tool(query, knowledge_base):

    query = query.lower()

    results = []

    for item in knowledge_base:
        if query in item.lower():
            results.append(item)

    if not results:
        return "No knowledge found"

    return "\n".join(results[:3])


def python_tool(code):

    try:
        local_scope = {}

        exec(code, {}, local_scope)

        return str(local_scope)

    except Exception as e:
        return str(e)
