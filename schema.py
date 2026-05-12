from pydantic import BaseModel, ConfigDict


class OutputSchema(BaseModel):
    """Unified structured record for benchmarking JSON validity."""

    model_config = ConfigDict(extra="forbid")

    query: str

    answer: str

    used_tool: bool

    used_rag: bool
