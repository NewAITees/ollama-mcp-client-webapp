import pytest
import asyncio
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from mcp import StdioServerParameters, types
from mcp_test_harness.mcp_client import list_server_tools, call_server_tool
from mcp_test_harness.models import Tool, ToolResponse

@pytest.fixture
def mock_server_param() -> StdioServerParameters:
    return StdioServerParameters(
        command="echo",
        args=["test"],
        env={"TEST_KEY": "test_value"}
    )

@pytest.mark.asyncio
async def test_list_server_tools(mock_server_param: StdioServerParameters) -> None:
    print("🔍 Starting test_list_server_tools")
    # スタブとなるツールリスト作成
    tool1 = types.Tool(
        name="test-tool-1",
        description="Test tool 1",
        inputSchema={"type": "object", "properties": {}}
    )
    tool2 = types.Tool(
        name="test-tool-2",
        description="Test tool 2",
        inputSchema={"type": "object", "properties": {}}
    )
    
    print("📦 Created test tools")
    
    # モックセッションとレスポンス
    mock_session = MagicMock()
    mock_tools_response = MagicMock()
    mock_tools_response.tools = [tool1, tool2]
    print(f"🎭 Created mock_tools_response: {mock_tools_response}")
    
    # 関数を呼び出し
    print("🔄 Calling list_server_tools")
    tools: List[Tool] = await list_server_tools(
        "test-server",
        mock_server_param,
        _test_session=mock_session,
        _test_tools_response=mock_tools_response
    )
    print(f"📦 Received tools: {tools}")
    
    # 検証
    print("🔍 Running assertions")
    assert isinstance(tools, list)
    assert len(tools) == 2
    assert tools[0].name == "test-tool-1"
    assert tools[1].name == "test-tool-2"
    print("✅ All assertions passed")

@pytest.mark.asyncio
async def test_call_server_tool(mock_server_param: StdioServerParameters) -> None:
    print("🔍 Starting test_call_server_tool")
    # ツール呼び出し結果をモック
    mock_result = MagicMock()
    mock_result.isError = False
    mock_result.content = {"result": "success"}
    print(f"🎭 Created mock_result: {mock_result}")

    # モックセッション
    mock_session = MagicMock()
    print("🎭 Created mock_session")

    # 関数を呼び出し
    print("🔄 Calling call_server_tool")
    result: ToolResponse = await call_server_tool(
        "test-server",
        mock_server_param,
        "test-tool",
        {"arg1": "value1"},
        _test_session=mock_session,
        _test_result=mock_result
    )
    print(f"📦 Received result: {result}")

    # 検証
    print("🔍 Running assertions")
    assert isinstance(result, ToolResponse)
    assert result.success is True
    assert "result" in result.result
    assert result.result["result"] == "success"
    
    # ログエントリの検証
    assert "timestamp" in result.log_entry
    assert result.log_entry["server"] == "test-server"
    assert result.log_entry["tool"] == "test-tool"
    assert result.log_entry["arguments"] == {"arg1": "value1"}
    assert result.log_entry["response"] == {"result": "success"}
    assert result.log_entry["is_error"] is False
    print("✅ All assertions passed") 