"""
OllamaMCPClient のテストケース
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from ollama_mcp.client import OllamaMCPClient
from ollama_mcp.models.multimodal import MultimodalModel

# テスト用の画像パス
TEST_IMAGES_DIR = Path(__file__).parent / "fixtures" / "images"
TEST_IMAGE_1 = TEST_IMAGES_DIR / "test1.jpg"
TEST_IMAGE_2 = TEST_IMAGES_DIR / "test2.jpg"

@pytest.fixture
def client():
    """クライアントのフィクスチャ"""
    return OllamaMCPClient(model_name="gemma")

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

@pytest.mark.asyncio
async def test_process_multimodal_query(client):
    """マルチモーダルクエリ処理のテスト"""
    # 接続状態を設定
    client.connected = True
    
    # モックのレスポンス
    mock_response = "Generated text about the images"
    
    # MultimodalModelをモック化
    mock_model = AsyncMock()
    mock_model.generate_with_images = AsyncMock(return_value=mock_response)
    
    with patch("ollama_mcp.client.MultimodalModel", return_value=mock_model):
        response = await client.process_multimodal_query(
            "Describe these images",
            [TEST_IMAGE_1, TEST_IMAGE_2]
        )
        
        assert response == mock_response
        mock_model.generate_with_images.assert_called_once()

@pytest.mark.asyncio
async def test_chat_with_images(client):
    """画像付きチャットのテスト"""
    # 接続状態を設定
    client.connected = True
    
    # モックのレスポンス
    mock_response = "Chat response about the images"
    
    # MultimodalModelをモック化
    mock_model = AsyncMock()
    mock_model.chat_with_images = AsyncMock(return_value=mock_response)
    
    with patch("ollama_mcp.client.MultimodalModel", return_value=mock_model):
        response = await client.chat_with_images(
            "What do you see in these images?",
            [TEST_IMAGE_1, TEST_IMAGE_2]
        )
        
        assert response == mock_response
        mock_model.chat_with_images.assert_called_once()

@pytest.mark.asyncio
async def test_process_multimodal_query_not_connected(client):
    """未接続状態でのマルチモーダルクエリ処理のテスト"""
    with pytest.raises(RuntimeError, match="Not connected to an MCP server"):
        await client.process_multimodal_query(
            "This should fail",
            [TEST_IMAGE_1]
        )

@pytest.mark.asyncio
async def test_chat_with_images_not_connected(client):
    """未接続状態での画像付きチャットのテスト"""
    with pytest.raises(RuntimeError, match="Not connected to an MCP server"):
        await client.chat_with_images(
            "This should fail",
            [TEST_IMAGE_1]
        ) 