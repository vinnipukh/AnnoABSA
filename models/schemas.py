from pydantic import BaseModel


class SaveTripletsRequest(BaseModel):
    """Request model for the primary save endpoint POST /review/{idx}/save."""
    triplets: list
    review_text: str | None = None


class AgentChatRequest(BaseModel):
    """Request model for the Helper Agent chat endpoint POST /agent/chat."""
    review_text: str
    model_a_triplets: list = []
    model_b_triplets: list = []
    user_message: str
    chat_history: list = []
