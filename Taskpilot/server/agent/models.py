from pydantic import BaseModel
from typing import Optional, Literal

class Step(BaseModel):
    action: Literal["navigate", "click", "type", "press", "scroll", "wait", "screenshot"]
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    key: Optional[str] = None
    amount: Optional[int] = None
    ms: Optional[int] = None
