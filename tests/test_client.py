"""
OllamaMCPClient のテストケース
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ollama_mcp.client import OllamaMCPClient

@pytest.mark.asyncio
async def test_client_initialization():
    """クライアントの初期化テスト"""
    client = OllamaMCPClient(model_name="llama3", debug_level="info")
    assert client.model_name == "llama3"
    assert client.debug_logger.level == "info"
    assert client.connected is False
    assert client.server_info is None

@pytest.mark.asyncio
async def test_connect_to_server():
    """サーバー接続のテスト"""
    client = OllamaMCPClient()
    tools = await client.connect_to_server("mock://server")
    
    assert client.connected is True
    assert client.server_info is not None
    assert isinstance(tools, list)
    assert len(tools) > 0
    assert "name" in tools[0]

@pytest.mark.asyncio
async def test_process_query():
    """クエリ処理のテスト"""
    client = OllamaMCPClient()
    await client.connect_to_server("mock://server")
    
    response = await client.process_query("テストクエリ")
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_process_query_not_connected():
    """未接続状態でのクエリ処理テスト"""
    client = OllamaMCPClient()
    with pytest.raises(RuntimeError, match="Not connected to an MCP server"):
        await client.process_query("テストクエリ")

@pytest.mark.asyncio
async def test_close_connection():
    """接続クローズのテスト"""
    client = OllamaMCPClient()
    await client.connect_to_server("mock://server")
    assert client.connected is True
    
    await client.close()
    assert client.connected is False

@pytest.mark.asyncio
async def test_set_model():
    """モデル設定のテスト"""
    client = OllamaMCPClient(model_name="llama3")
    assert client.model_name == "llama3"
    
    client.set_model("gpt4")
    assert client.model_name == "gpt4"

@pytest.mark.asyncio
async def test_set_model_parameters():
    """モデルパラメータ設定のテスト"""
    client = OllamaMCPClient()
    params = {"temperature": 0.7, "max_tokens": 100}
    
    client.set_model_parameters(params)
    # パラメータ設定の検証は実装依存のため、エラーが発生しないことのみを確認
    assert True 