import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from ollama_mcp.agno_integration import OllamaMCPIntegration
from agno.agent import Agent
from agno.models.ollama import Ollama

@pytest.fixture
def client():
    """テスト用のOllamaMCPIntegrationインスタンスを作成"""
    return OllamaMCPIntegration(model_name="llama3")

@pytest.mark.asyncio
async def test_client_initialization(client):
    """クライアントの初期化テスト"""
    assert client.model_name == "llama3"
    assert client.debugger is not None
    assert client.agent is None
    assert client.mcp_tools is None
    assert client.connected is False
    assert client.server_info is None

@pytest.mark.asyncio
async def test_connect_to_server(client):
    """サーバー接続テスト"""
    mock_tools = [
        {"name": "test_tool", "description": "Test tool"},
        {"name": "another_tool", "description": "Another test tool"}
    ]
    
    mock_env = {"PATH": "/usr/local/bin"}
    mock_session = AsyncMock()
    mock_session.get_resource = AsyncMock(
        return_value={"actions": {"test": {"description": "Test action", "parameters": {}}}}
    )
    
    with patch('ollama_mcp.agno_integration.StdioServerParameters') as mock_params, \
         patch('agno.tools.mcp.MCPTools') as mock_mcp_tools, \
         patch('agno.agent.Agent') as mock_agent:
        
        # MCPツールのモック設定
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.mcp_resources = mock_tools
        mock_mcp_instance.session = mock_session
        mock_mcp_tools.return_value.__aenter__.return_value = mock_mcp_instance
        
        # パラメータとエージェントの設定
        mock_params.return_value = Mock(env=mock_env)
        mock_agent.return_value = Mock(spec=Agent)
        
        tools = await client.connect_to_server("test_server.py")
        
        # アサーション
        assert len(tools) == 2
        assert tools[0]["name"] == "test_tool.test"
        assert tools[1]["name"] == "another_tool.test"
        assert client.connected is True
        assert client.server_info is not None
        assert client.server_info["tools_count"] == 2
        
        # モックの呼び出し確認
        mock_params.assert_called_once()
        mock_mcp_tools.assert_called_once()
        mock_agent.assert_called_once()

@pytest.mark.asyncio
async def test_process_query(client):
    """クエリ処理テスト"""
    test_query = "テストクエリ"
    mock_response = Mock(response="テストレスポンス")
    
    with patch('agno.agent.Agent') as mock_agent:
        mock_agent_instance = Mock(spec=Agent)
        mock_agent_instance.arun = AsyncMock(return_value=mock_response)
        client.agent = mock_agent_instance
        client.connected = True
        
        response = await client.process_query(test_query)
        
        assert response == "テストレスポンス"
        mock_agent_instance.arun.assert_called_once_with(test_query)

@pytest.mark.asyncio
async def test_process_multimodal_query(client):
    """マルチモーダルクエリ処理テスト"""
    test_query = "画像について説明してください"
    test_images = ["test_image.jpg"]
    mock_response = Mock(response="画像の説明")
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('agno.media.Image', autospec=True) as mock_image, \
         patch('agno.agent.Agent') as mock_agent:
        
        mock_agent_instance = Mock(spec=Agent)
        mock_agent_instance.arun = AsyncMock(return_value=mock_response)
        client.agent = mock_agent_instance
        client.connected = True
        mock_image.return_value = Mock()
        
        response = await client.process_multimodal_query(test_query, test_images)
        
        assert response == "画像の説明"
        mock_agent_instance.arun.assert_called_once()
        mock_image.assert_called_once_with(path=test_images[0])

@pytest.mark.asyncio
async def test_stream_query(client):
    """ストリーミングクエリ処理テスト"""
    test_query = "ストリーミングテスト"
    mock_chunks = ["チャンク1", "チャンク2", "チャンク3"]
    
    async def mock_stream():
        for chunk in mock_chunks:
            yield Mock(response=chunk)
            await asyncio.sleep(0.1)
    
    with patch('agno.agent.Agent') as mock_agent:
        mock_agent_instance = Mock(spec=Agent)
        mock_agent_instance.astream = AsyncMock(return_value=mock_stream())
        client.agent = mock_agent_instance
        client.connected = True
        
        # コールバックのモック
        mock_callback = AsyncMock()
        
        # ストリーミング処理のテスト
        response = await client.stream_query(test_query, callback=mock_callback)
        
        assert response == "チャンク1チャンク2チャンク3"
        mock_agent_instance.astream.assert_called_once_with(test_query)
        assert mock_callback.call_count == 3

@pytest.mark.asyncio
async def test_error_handling(client):
    """エラー処理テスト"""
    test_errors = [
        ("connection_error", "接続エラー", StdioServerParameters),
        ("query_error", "クエリ処理エラー", "process_query"),
        ("multimodal_error", "マルチモーダル処理エラー", "process_multimodal_query"),
        ("streaming_error", "ストリーミングエラー", "stream_query")
    ]
    
    for error_type, error_msg, target in test_errors:
        if isinstance(target, str):
            # メソッドエラーのテスト
            with patch.object(client, target) as mock_method:
                mock_method.side_effect = Exception(error_msg)
                
                with pytest.raises(Exception) as exc_info:
                    if target == "process_query":
                        await client.process_query("test")
                    elif target == "process_multimodal_query":
                        await client.process_multimodal_query("test", ["test.jpg"])
                    else:
                        await client.stream_query("test")
                
                assert str(exc_info.value) == error_msg
        else:
            # 接続エラーのテスト
            with patch('ollama_mcp.agno_integration.StdioServerParameters') as mock_params:
                mock_params.side_effect = Exception(error_msg)
                
                with pytest.raises(Exception) as exc_info:
                    await client.connect_to_server("test_server.py")
                
                assert str(exc_info.value) == error_msg

@pytest.mark.asyncio
async def test_close(client):
    """クライアント終了テスト"""
    mock_mcp_tools = AsyncMock()
    mock_mcp_tools.__aexit__ = AsyncMock()
    client.mcp_tools = mock_mcp_tools
    client.connected = True
    
    await client.close()
    
    assert client.mcp_tools is None
    assert client.agent is None
    assert client.connected is False
    mock_mcp_tools.__aexit__.assert_called_once_with(None, None, None)

@pytest.mark.asyncio
async def test_set_model(client):
    """モデル設定テスト"""
    new_model = "gemma"
    
    # 未接続状態でのモデル変更
    client.set_model(new_model)
    assert client.model_name == new_model
    
    # 接続状態でのモデル変更
    client.connected = True
    client.set_model(new_model)
    assert client.model_name == new_model

@pytest.mark.asyncio
async def test_set_model_parameters(client):
    """モデルパラメータ設定テスト"""
    test_params = {
        "temperature": 0.7,
        "top_p": 0.9
    }
    
    # エージェントなしの場合
    client.set_model_parameters(test_params)
    
    # エージェントありの場合
    mock_agent = Mock(spec=Agent)
    mock_agent.model = Mock()
    mock_agent.model.parameters = {}
    client.agent = mock_agent
    
    client.set_model_parameters(test_params)
    assert client.agent.model.parameters == test_params 