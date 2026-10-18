import uuid
from pydantic import BaseModel
from typing import Optional
from app.models.comment import CommentCategory, CommentSeverity


class CommentResponse(BaseModel):
    id: uuid.UUID
    category: CommentCategory
    severity: CommentSeverity
    line_number: Optional[int]
    message: str
    suggestion: str
    reference: Optional[str]

    model_config = {"from_attributes": True}
