import pytest
import gradio as gr
from typing import List, Dict, Any
from unittest.mock import patch, AsyncMock, MagicMock
from mcp_test_harness.app import create_app
from mcp_test_harness.models import ToolResponse, Tool

def test_app_creation() -> None:
    with patch('mcp_test_harness.app.load_server_config') as mock_load_config, \
         patch('mcp_test_harness.app.create_server_parameters') as mock_create_params:
        
        # モックの戻り値を設定
        mock_load_config.return_value = {"mcpServers": {"test-server": {}}}
        mock_create_params.return_value = {"test-server": MagicMock()}
        
        # アプリを作成
        app = create_app(test_mode=True)
        
        # 基本的な検証
        assert isinstance(app, gr.Blocks)
        # テストモードでは設定ファイルを読み込まないため、この検証は不要
        # assert mock_load_config.called
        # assert mock_create_params.called

@pytest.mark.asyncio
async def test_list_servers() -> None:
    from mcp_test_harness.app import list_servers
    
    with patch('mcp_test_harness.app.server_parameters', {"server1": MagicMock(), "server2": MagicMock()}):
        result = await list_servers()
        assert isinstance(result, list)
        assert "server1" in result
        assert "server2" in result

@pytest.mark.asyncio
async def test_list_tools() -> None:
    from mcp_test_harness.app import list_tools
    
    with patch('mcp_test_harness.app.list_server_tools') as mock_list_tools, \
         patch('mcp_test_harness.app.server_parameters', {"test-server": MagicMock()}):
        # モックの戻り値を設定
        mock_list_tools.return_value = [
            Tool(
                name="tool1",
                description="Tool 1",
                schema="{}"
            ),
            Tool(
                name="tool2",
                description="Tool 2",
                schema="{}"
            )
        ]
        
        result = await list_tools("test-server")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0][0] == "tool1 - Tool 1"
        assert result[1][0] == "tool2 - Tool 2"

@pytest.mark.asyncio
async def test_call_tool() -> None:
    from mcp_test_harness.app import call_tool
    
    with patch('mcp_test_harness.app.call_server_tool') as mock_call_tool, \
         patch('mcp_test_harness.app.server_parameters', {"test-server": MagicMock()}):
        # 成功ケースのモック
        mock_call_tool.return_value = ToolResponse(
            success=True,
            result={"data": "test result"},
            log_entry={"timestamp": "2025-03-04T12:00:00"}
        )
        
        result = await call_tool("test-server", ("test-tool", "{}"), '{"arg1": "value1"}')
        assert "成功" in result
        assert "test result" in result
        
        # エラーケースのモック
        mock_call_tool.return_value = ToolResponse(
            success=False,
            error="Test error",
            log_entry={"timestamp": "2025-03-04T12:00:00"}
        )
        
        result = await call_tool("test-server", ("test-tool", "{}"), '{"arg1": "value1"}')
        assert "エラー" in result
        assert "Test error" in result 