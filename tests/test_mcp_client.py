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
    
    # ClientSession.list_toolsの戻り値をモック
    mock_tools_result = MagicMock()
    mock_tools_result.tools = [tool1, tool2]
    print(f"🎭 Created mock_tools_result: {mock_tools_result}")
    
    # セッションをモック
    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
    print("🎭 Created mock_session")
    
    # ClientSessionをモック
    with patch('mcp_test_harness.mcp_client.stdio_client') as mock_stdio_client, \
         patch('mcp_test_harness.mcp_client.ClientSession', return_value=mock_session):
        
        print("🎭 Applied patches")
        
        # stdio_clientからの戻り値をモック
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio_client.return_value.__aenter__.return_value = (mock_read, mock_write)
        print("🎭 Set up stdio_client mock")
        
        # 関数を呼び出し
        print("🔄 Calling list_server_tools")
        tools: List[Tool] = await list_server_tools("test-server", mock_server_param)
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
    
    # セッションをモック
    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)
    print("🎭 Created mock_session")
    
    # ClientSessionをモック
    with patch('mcp_test_harness.mcp_client.stdio_client') as mock_stdio_client, \
         patch('mcp_test_harness.mcp_client.ClientSession', return_value=mock_session), \
         patch('mcp_test_harness.mcp_client.log_request_response') as mock_log:
        
        print("🎭 Applied patches")
        
        # stdio_clientからの戻り値をモック
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio_client.return_value.__aenter__.return_value = (mock_read, mock_write)
        print("🎭 Set up stdio_client mock")
        
        # モックログエントリ
        mock_log.return_value = {"timestamp": "2025-03-04T12:00:00"}
        print("🎭 Set up mock_log")
        
        # 関数を呼び出し
        print("🔄 Calling call_server_tool")
        result: ToolResponse = await call_server_tool(
            "test-server",
            mock_server_param,
            "test-tool",
            {"arg1": "value1"}
        )
        print(f"📦 Received result: {result}")
        
        # 検証
        print("🔍 Running assertions")
        assert isinstance(result, ToolResponse)
        assert result.success is True
        assert result.result == {"result": "success"}
        assert result.log_entry == {"timestamp": "2025-03-04T12:00:00"}
        print("✅ All assertions passed") 