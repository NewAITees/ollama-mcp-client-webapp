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

@pytest.mark.asyncio
async def test_list_tools_with_list_input() -> None:
    """リスト型の入力が渡された場合のテスト"""
    from mcp_test_harness.app import list_tools
    
    with patch('mcp_test_harness.app.list_server_tools') as mock_list_tools, \
         patch('mcp_test_harness.app.server_parameters', {"test-server": MagicMock()}):
        # モックの戻り値を設定
        mock_list_tools.return_value = [
            Tool(
                name="tool1",
                description="Tool 1",
                schema="{}"
            )
        ]
        
        # リスト型の入力でテスト
        result = await list_tools(["test-server"])
        assert isinstance(result, list)
        assert len(result) == 1  # リストの最初の要素が使用されるため、1つのツールが返される
        assert result[0][0] == "tool1 - Tool 1"  # ツール名と説明が正しく結合されていることを確認

@pytest.mark.asyncio
async def test_list_tools_with_invalid_input() -> None:
    """無効な入力が渡された場合のテスト"""
    from mcp_test_harness.app import list_tools
    
    with patch('mcp_test_harness.app.list_server_tools') as mock_list_tools, \
         patch('mcp_test_harness.app.server_parameters', {"test-server": MagicMock()}):
        # 空の文字列
        result = await list_tools("")
        assert isinstance(result, list)
        assert len(result) == 0
        
        # None
        result = await list_tools(None)
        assert isinstance(result, list)
        assert len(result) == 0
        
        # 存在しないサーバー
        result = await list_tools("non-existent-server")
        assert isinstance(result, list)
        assert len(result) == 0

@pytest.mark.asyncio
async def test_list_tools_with_error() -> None:
    """エラーが発生した場合のテスト"""
    from mcp_test_harness.app import list_tools
    
    with patch('mcp_test_harness.app.list_server_tools') as mock_list_tools, \
         patch('mcp_test_harness.app.server_parameters', {"test-server": MagicMock()}):
        # エラーを発生させる
        mock_list_tools.side_effect = Exception("Test error")
        
        result = await list_tools("test-server")
        assert isinstance(result, list)
        assert len(result) == 0

@pytest.mark.asyncio
async def test_get_tool_schema_with_invalid_input() -> None:
    """無効な入力が渡された場合のスキーマ取得テスト"""
    from mcp_test_harness.app import get_tool_schema
    
    # 空のタプル
    result = await get_tool_schema("test-server", ())
    assert result == "{}"
    
    # 要素が1つだけのタプル
    result = await get_tool_schema("test-server", ("tool1",))
    assert result == "{}"
    
    # None
    result = await get_tool_schema("test-server", None)
    assert result == "{}"

@pytest.mark.asyncio
async def test_get_tool_schema_with_error() -> None:
    """エラーが発生した場合のスキーマ取得テスト"""
    from mcp_test_harness.app import get_tool_schema
    
    # 不正なタプル構造
    result = await get_tool_schema("test-server", ("tool1", "schema", "extra"))
    assert result == "{}"
    
    # スキーマがNoneの場合
    result = await get_tool_schema("test-server", ("tool1", None))
    assert result == "{}"

@pytest.mark.asyncio
async def test_create_app_with_invalid_config() -> None:
    """無効な設定でのアプリケーション作成テスト"""
    from mcp_test_harness.app import create_app
    
    with patch('mcp_test_harness.app.load_server_config') as mock_load_config, \
         patch('mcp_test_harness.app.create_server_parameters') as mock_create_params:
        # 設定読み込みでエラーを発生させる
        mock_load_config.side_effect = Exception("Config error")
        
        app = create_app()
        assert app is not None
        # グローバル変数が空の辞書に設定されていることを確認
        from mcp_test_harness.app import server_config, server_parameters
        assert server_config == {}
        assert server_parameters == {} 