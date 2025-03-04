from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class Tool(BaseModel):
    """MCPツールのモデル"""
    name: str
    description: str
    schema: str = Field(alias="schema")

class ToolResponse(BaseModel):
    """ツール呼び出しのレスポンスモデル"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    log_entry: Dict[str, Any]

class ServerConfig(BaseModel):
    """サーバー設定のモデル"""
    command: str
    args: List[str]
    env: Dict[str, str] = Field(default_factory=dict)
    alwaysAllow: Optional[List[str]] = None
    defaultArguments: Optional[Dict[str, Any]] = None 