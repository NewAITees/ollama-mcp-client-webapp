"""
MCP ツールのテストケース
"""
import pytest
from typing import Dict, Any

from ollama_mcp.tools.base import Tool
from ollama_mcp.tools.registry import ToolRegistry

async def sample_tool_func(**kwargs) -> Dict[str, Any]:
    """サンプルツール関数"""
    return {"result": "success", "args": kwargs}

def test_tool_initialization():
    """ツール初期化のテスト"""
    tool = Tool(
        name="test_tool",
        description="Test tool description",
        input_schema={"type": "object", "properties": {}},
        func=sample_tool_func
    )
    
    assert tool.name == "test_tool"
    assert tool.description == "Test tool description"
    assert callable(tool.func)

@pytest.mark.asyncio
async def test_tool_execution():
    """ツール実行のテスト"""
    tool = Tool(
        name="test_tool",
        description="Test tool description",
        input_schema={"type": "object", "properties": {}},
        func=sample_tool_func
    )
    
    result = await tool(test_arg="value")
    assert result["result"] == "success"
    assert result["args"]["test_arg"] == "value"

def test_tool_registry():
    """ツールレジストリのテスト"""
    registry = ToolRegistry()
    
    # ツールの登録
    tool_def = {
        "name": "test_tool",
        "description": "Test tool description",
        "inputSchema": {"type": "object", "properties": {}}
    }
    registry.register_tool(tool_def)
    
    # ツールの取得
    tool = registry.get_tool("test_tool")
    assert tool is not None
    assert tool["name"] == "test_tool"
    
    # ツール一覧の取得
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "test_tool"

def test_tool_registry_validation():
    """ツールレジストリのバリデーションテスト"""
    registry = ToolRegistry()
    
    # ツールの登録
    tool_def = {
        "name": "test_tool",
        "description": "Test tool description",
        "inputSchema": {
            "type": "object",
            "properties": {
                "arg1": {"type": "string"}
            },
            "required": ["arg1"]
        }
    }
    registry.register_tool(tool_def)
    
    # 有効な引数での検証
    assert registry.validate_tool_call("test_tool", {"arg1": "test"}) is True
    
    # 存在しないツールの検証
    assert registry.validate_tool_call("non_existent_tool", {}) is False

@pytest.mark.asyncio
async def test_tool_decorator():
    """ツールデコレータのテスト"""
    @Tool.register(
        name="decorated_tool",
        description="Decorated tool description",
        input_schema={"type": "object", "properties": {}}
    )
    async def decorated_tool_func(**kwargs):
        return {"status": "ok"}
    
    assert isinstance(decorated_tool_func, Tool)
    assert decorated_tool_func.name == "decorated_tool"
    
    result = await decorated_tool_func()
    assert result["status"] == "ok" 