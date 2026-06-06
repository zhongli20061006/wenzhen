from pydantic import BaseModel
from typing import Optional


class FeedbackRequest(BaseModel):
    registration_id: int
    is_correct: bool
    actual_department_id: int
    doctor_note: Optional[str] = None
