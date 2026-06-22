from pydantic import BaseModel
from typing import Optional


class FeedbackRequest(BaseModel):
    registration_id: int
    is_correct: bool
    actual_department_id: int
    error_reason: Optional[str] = None
    doctor_note: Optional[str] = None
