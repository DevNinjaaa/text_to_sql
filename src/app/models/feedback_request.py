from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class FeedbackRequest(BaseModel):
    template_id: str
    user_phrase: str
    is_correct: bool
    
    # These provide context for the AI fix
    matched_sql: Optional[str]
    extracted_params: Optional[Dict[str, Any]] 
    user_comment: str