from pydantic import BaseModel, Field


class ScanAgentInput(BaseModel):
    image_url: str


class ScanAgentOutput(BaseModel):
    card_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
