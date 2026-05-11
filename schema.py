from pydantic import BaseModel

class OutputSchema(BaseModel):
    query: str
    answer: str
    used_tool: bool
    used_rag: bool
