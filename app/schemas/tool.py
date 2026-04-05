from pydantic import BaseModel
from typing import List, Optional

class ToolParameter(BaseModel):
    name: str
    type: str  # e.g., "string", "integer", "boolean"
    required: bool

class ManualToolCreate(BaseModel):
    name: str
    description: str
    base_url: str
    endpoint_path: str
    method: str  # e.g., "GET", "POST", "PUT", "DELETE"
    parameters: List[ToolParameter]
