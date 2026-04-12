from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class SQLResponse(BaseModel):
    status: str  
    message: str
    matched_sql: Optional[str] = None
    template_id: Optional[str] = None
    distance: Optional[float] = None
    extracted_params: Optional[Dict[str, Any]] = None